"""Silver data-quality report: rows in/out per step and rows affected per rule.

Writes ``reports/dq_report.md`` after ``dbt build`` (``make dq``; ``make dbt`` runs it).
CLAUDE.md asks for row counts in and out, with the reason, for every step that filters
rows, and docs/04 §2 for rows affected per cleaning rule. Four sections:

1. **Steps.** Rows from bronze to each silver model. Silver removes rows in one place only
   (C1 de-duplication); every other step splits or flags.
2. **Flags by rule.** Every column that carries ``meta.dq_rule`` in the dbt YAML, read from
   ``dbt/target/manifest.json``. A new flag shows up here as soon as it is documented,
   so the report can't silently miss one. Rows and AED affected (AED from the model's
   ``meta.dq_amount_column``, which is always a once-per-deal / once-per-contract column).
3. **Populations.** How many rows reach the clean market-sale and market-rent populations,
   and the first rule that excludes each of the rest (a waterfall, so reasons add up).
4. **Reconciliation.** AED counted once per deal / contract against the Phase 1 figures.
5. **Mortgage indicator inputs.** Purchase mortgages matched to a same-day ready sale vs
   ready market sales by year (the KPI), new mortgages per 100 market sales (secondary),
   and portfolio mortgage registrations reported separately, once per deal.

All counting is SQL; only the small result tables come back to Python.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg

from dubai_property import config, db

log = logging.getLogger(__name__)

REPORT_PATH = config.REPORTS / "dq_report.md"
MANIFEST_PATH = config.DBT_DIR / "target" / "manifest.json"
PACKAGE = "dubai_property"


@dataclass(frozen=True)
class Flag:
    """One boolean flag column documented with ``meta.dq_rule``."""

    model: str
    relation: str
    column: str
    rule: str
    description: str
    amount_column: str | None


def _meta(obj: dict[str, Any]) -> dict[str, Any]:
    """``meta`` of a manifest node or column (dbt 1.10+ also nests it under ``config``)."""
    return {**(obj.get("config", {}) or {}).get("meta", {}), **(obj.get("meta") or {})}


def rule_sort_key(rule: str) -> tuple[int, str]:
    """C4 before C16: sort rules by their number, not as text."""
    match = re.fullmatch(r"C(\d+)", rule)
    return (int(match.group(1)) if match else 10_000, rule)


def flags_from_manifest(manifest: dict[str, Any]) -> list[Flag]:
    """Every documented flag column of this project's models, ordered by rule then model."""
    flags = []
    for node in manifest.get("nodes", {}).values():
        if node.get("resource_type") != "model" or node.get("package_name") != PACKAGE:
            continue
        amount = _meta(node).get("dq_amount_column")
        for col in node.get("columns", {}).values():
            rule = _meta(col).get("dq_rule")
            if rule:
                flags.append(
                    Flag(
                        model=node["name"],
                        relation=node["relation_name"],
                        column=col["name"],
                        rule=str(rule),
                        description=" ".join((col.get("description") or "").split()),
                        amount_column=amount,
                    )
                )
    return sorted(flags, key=lambda f: (rule_sort_key(f.rule), f.model, f.column))


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    """Read the dbt manifest written by ``dbt build`` / ``dbt compile``."""
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: run `make dbt` (dbt build) first")
    return json.loads(path.read_text())


# --- SQL ------------------------------------------------------------------------------

STEPS_SQL = """
select 'bronze.dld_transactions' as step, count(*) as rows_out,
       null::bigint as rows_removed, 'raw lines as loaded' as reason
from bronze.dld_transactions
union all
select 'silver.stg_transactions', count(*),
       (select count(*) from bronze.dld_transactions) - count(*),
       'C1: older snapshot of a transaction_id removed'
from silver.stg_transactions
union all
select 'silver.int_transaction_deal_groups', count(*),
       (select count(*) from silver.stg_transactions) - count(*), 'none (adds C16 columns)'
from silver.int_transaction_deal_groups
union all
select 'silver.int_market_sales', count(*), null,
       'split: Sales + Gifts groups (flags only, nothing removed)'
from silver.int_market_sales
union all
select 'silver.int_mortgages', count(*), null,
       'split: Mortgages group (flags only, nothing removed)'
from silver.int_mortgages
union all
select 'bronze.dld_rent_contracts', count(*), null, 'raw lines as loaded'
from bronze.dld_rent_contracts
union all
select 'silver.int_rent_contracts', count(*),
       (select count(*) from bronze.dld_rent_contracts) - count(*),
       'C1: older snapshot of a (contract_id, line_number) removed'
from silver.int_rent_contracts
"""

# First rule that keeps a row out of the clean population, in a fixed order.
SALES_WATERFALL_SQL = """
select reason, count(*) as rows, round(sum(actual_worth_once_aed) / 1e9, 2) as aed_bn
from (
    select actual_worth_once_aed, case
        when not is_market_sale then '0 not a market sale (C3: gift, development, lease-to-own)'
        when is_date_invalid then '1 C18 date invalid'
        when is_pre_2004 then '2 C18 before 2004'
        when is_repeated_deal_value then '3 C16 repeated deal value'
        when is_price_below_floor then '4 C4 price below AED 50k'
        when is_ppsqm_outlier then '5 C4 price per sq m outside band'
        when is_area_invalid then '6 C5 implausible area'
        when is_ppsqm_mismatch then '7 C6 price per sq m mismatch'
        else '8 clean market sale'
    end as reason
    from silver.int_market_sales
) t
group by 1 order by 1
"""

RENT_WATERFALL_SQL = """
select reason, count(*) as lines, round(sum(annual_rent_alloc_aed) / 1e9, 2) as aed_bn
from (
    select annual_rent_alloc_aed, case
        when not is_new then '0 C13 renewal'
        when is_multi_unit then '1 C11 multi-unit contract'
        when is_non_market_property_type then '2 C20 virtual unit / labour camp'
        when is_date_invalid then '3 C18 start date invalid'
        when is_start_after_snapshot then '4 C18 starts after the data snapshot'
        when is_pre_2004 then '5 C18 before 2004'
        when is_end_date_implausible then '6 C18 end date implausible'
        when is_rent_outlier then '7 C14 outlier'
        else '8 market rent'
    end as reason
    from silver.int_rent_contracts
) t
group by 1 order by 1
"""

RECON_SQL = """
with actual as (
    select 'transactions' as dataset, trans_group, 'naive_total_bn' as metric,
           round(sum(actual_worth_aed) / 1e9, 1) as actual
    from silver.int_transaction_deal_groups group by 2
    union all
    select 'transactions', trans_group, 'once_per_deal_bn',
           round(sum(actual_worth_once_aed) / 1e9, 1)
    from silver.int_transaction_deal_groups group by 2
    union all
    select 'transactions', trans_group, 'overstated_bn',
           round((sum(actual_worth_aed) - sum(actual_worth_once_aed)) / 1e9, 1)
    from silver.int_transaction_deal_groups group by 2
    union all
    select 'transactions', trans_group, 'repeated_groups',
           count(distinct deal_group_id) filter (where is_repeated_deal_value)
    from silver.int_transaction_deal_groups group by 2
    union all
    select 'transactions', trans_group, 'repeated_lines',
           count(*) filter (where is_repeated_deal_value)
    from silver.int_transaction_deal_groups group by 2
    union all
    select 'transactions', trans_group, 'similar_size_groups', count(distinct batch_group_id)
    from silver.int_transaction_deal_groups group by 2
    union all
    select 'transactions', trans_group, 'similar_size_lines',
           count(*) filter (where is_similar_size_batch)
    from silver.int_transaction_deal_groups group by 2
    union all
    select 'rents', null, m, v from (
        select count(distinct contract_id)::numeric as contracts,
               count(distinct contract_id) filter (where is_multi_unit)::numeric as multi_c,
               count(*) filter (where is_multi_unit)::numeric as multi_l,
               round(sum(annual_amount_aed) / 1e9, 1) as naive,
               round(sum(annual_rent_alloc_aed) / 1e9, 1) as once
        from silver.int_rent_contracts
    ) t cross join lateral (values ('contracts', contracts), ('multi_line_contracts', multi_c),
                                   ('multi_line_lines', multi_l), ('naive_total_bn', naive),
                                   ('once_per_contract_bn', once)) v (m, v)
)
select a.dataset, coalesce(a.trans_group, '') as trans_group, a.metric,
       e.expected_value as phase1, a.actual,
       case when e.expected_value is null then ''
            when e.expected_value = a.actual then 'match' else 'DIFFERENT' end as check
from actual a
left join silver.seed_phase1_reconciliation e
  on e.dataset = a.dataset and e.metric = a.metric
 and coalesce(e.trans_group, '') = coalesce(a.trans_group, '')
order by 1, 2, 3
"""


# docs/01 §4: purchase-mortgage share of ready sales = ready market sales matched to a
# same-day purchase mortgage (silver.int_purchase_mortgage_pairs) / ready market sales, by
# registration year; a lower bound. Secondary: new mortgages (incl. refinancing) per 100
# market sales. Portfolio registrations sit outside both; their deals and values are
# counted once per deal (C16). Only dated, in-scope rows count.
MORTGAGE_SHARE_SQL = """
with sales as (
    select extract(year from txn_date)::int as yr, count(*) as market_sales,
           count(*) filter (where not is_offplan) as ready_sales
    from silver.int_market_sales
    where is_market_sale and not is_date_invalid and not is_pre_2004
    group by 1
),
pairs as (
    select extract(year from txn_date)::int as yr, count(*) as purchase_mortgages
    from silver.int_purchase_mortgage_pairs
    where txn_date >= date '2004-01-01'
    group by 1
),
mortgages as (
    select extract(year from txn_date)::int as yr,
           count(*) filter (where is_new_mortgage) as new_mortgages,
           round(sum(mortgage_amount_once_aed) filter (where is_new_mortgage) / 1e9, 1)
               as loans_bn,
           count(distinct deal_group_id) filter (where is_portfolio_mortgage) as portfolio_deals,
           count(*) filter (where is_portfolio_mortgage) as portfolio_lines,
           round(sum(portfolio_mortgage_value_once_aed) / 1e9, 2) as portfolio_value_bn
    from silver.int_mortgages
    where not is_date_invalid and not is_pre_2004
    group by 1
)
select coalesce(s.yr, m.yr)::text as year, s.market_sales, s.ready_sales,
       coalesce(p.purchase_mortgages, 0) as purchase_mortgages,
       round(100.0 * coalesce(p.purchase_mortgages, 0) / nullif(s.ready_sales, 0), 1)
           as purchase_mortgage_share_pct,
       m.new_mortgages,
       round(100.0 * m.new_mortgages / nullif(s.market_sales, 0), 1) as new_per_100_sales,
       m.loans_bn, m.portfolio_deals, m.portfolio_lines, m.portfolio_value_bn
from sales s full outer join mortgages m using (yr) left join pairs p using (yr)
order by 1
"""


def flag_counts(conn: psycopg.Connection, flags: list[Flag]) -> list[tuple]:
    """Rows and AED affected per flag: one scan per model."""
    by_model: dict[str, list[Flag]] = {}
    for f in flags:
        by_model.setdefault(f.relation, []).append(f)
    results: dict[tuple[str, str], tuple] = {}
    for relation, model_flags in by_model.items():
        amount = model_flags[0].amount_column
        parts = ["count(*)"]
        for f in model_flags:
            parts.append(f'count(*) filter (where "{f.column}")')
            parts.append(f'sum("{amount}") filter (where "{f.column}")' if amount else "null")
        row = conn.execute(f"select {', '.join(parts)} from {relation}").fetchone()
        total = row[0]
        for i, f in enumerate(model_flags):
            n, aed = row[1 + 2 * i], row[2 + 2 * i]
            results[(f.relation, f.column)] = (
                f.rule,
                f"`{f.model}.{f.column}`",
                n,
                round(100 * n / total, 2) if total else None,
                round(aed / Decimal(1e9), 2) if aed is not None else None,
                f.description,
            )
    return [results[(f.relation, f.column)] for f in flags]


# --- Rendering ------------------------------------------------------------------------


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, int | Decimal) and value == int(value) and abs(value) >= 1000:
        return f"{int(value):,}"
    return str(value).replace("|", "\\|")


def md_table(columns: list[str], rows: list[tuple]) -> list[str]:
    """A markdown table (values with thousands separators, pipes escaped)."""
    out = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    out += ["| " + " | ".join(_cell(v) for v in row) + " |" for row in rows]
    return out


def run(path: Path = REPORT_PATH, manifest_path: Path = MANIFEST_PATH) -> Path:
    """Query silver and write the report."""
    flags = flags_from_manifest(load_manifest(manifest_path))
    t0 = time.perf_counter()
    with db.connect() as conn:
        conn.execute("set work_mem = '512MB'")
        (pg_db,) = conn.execute("select current_database()").fetchone()
        steps = conn.execute(STEPS_SQL).fetchall()
        counts = flag_counts(conn, flags)
        sales = conn.execute(SALES_WATERFALL_SQL).fetchall()
        rents = conn.execute(RENT_WATERFALL_SQL).fetchall()
        recon = conn.execute(RECON_SQL).fetchall()
        share = conn.execute(MORTGAGE_SHARE_SQL).fetchall()
        conn.rollback()
    lines = [
        "# Data-quality report: silver",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `quality/dq_report.py` from database "
        f"`{pg_db}`. Regenerate with `make dq` (after `make dbt`). The rules are in docs/04 §2.",
        "",
        "## 1. Rows in and out per step",
        "",
        "Silver removes rows in one place only: C1 keeps the latest snapshot of each line. "
        "Every other rule is a flag. The dbt tests `recon_transactions_partition` and "
        "`recon_rents_rows` enforce these counts.",
        "",
        *md_table(["Step", "Rows", "Removed", "Reason"], steps),
        "",
        "## 2. Rows affected per rule",
        "",
        "Every column documented with `meta.dq_rule` in the dbt YAML. Flags overlap, so rows "
        "don't add up across rules. AED is once per deal (transactions, "
        "`actual_worth_once_aed`) or allocated per line (rents, `annual_rent_alloc_aed`), so "
        "it never double-counts a portfolio deal or a multi-unit contract.",
        "",
        *md_table(["Rule", "Flag", "Rows", "% of model", "AED bn", "Meaning"], counts),
        "",
        "## 3. Populations",
        "",
        "Each row is counted once, under the **first** reason that keeps it out (in the "
        "order shown), so the rows add up to the model total.",
        "",
        "**Clean market sales** (`int_market_sales.is_clean_market_sale`): the population for "
        "prices, indices, yields and the AVM.",
        "",
        *md_table(["Reason", "Rows", "AED bn"], sales),
        "",
        "**Market rents** (`int_rent_contracts.is_market_rent`): the population for market rent "
        "and yields.",
        "",
        *md_table(["Reason", "Lines", "Allocated AED bn"], rents),
        "",
        "## 4. Reconciliation with Phase 1",
        "",
        "AED counted once per deal / contract, and the C16 / C11 counts, against "
        "`seed_phase1_reconciliation` (reports/phase1_findings.md). `phase1` is blank where "
        "Phase 1 published no figure. On any other data than the Phase 1 snapshot (e.g. the "
        "CI fixtures) the figures are expected to differ; the dbt tests "
        "`recon_*_phase1_figures` only check them on that snapshot, and "
        "`recon_*_once_vs_*` check the method on any data.",
        "",
        *md_table(["Dataset", "Group", "Metric", "Phase 1", "Silver", "Check"], recon),
        "",
        "## 5. Mortgage indicator inputs",
        "",
        "**Purchase-mortgage share of ready sales** (docs/01 §4) = ready market sales matched "
        "to a Mortgage Registration / Delayed Mortgage of the same unit on the same day "
        "(`int_purchase_mortgage_pairs`) / ready market sales, by registration year. It is a "
        "lower bound: loans registered on another day or keyed differently don't match. "
        "**New mortgages per 100 market sales** is the secondary indicator: individual new "
        "mortgages (Mortgage Registration, Delayed Mortgage, Mortgage Pre-Registration, "
        "`is_new_mortgage`) include refinancing and loans on units bought earlier. "
        "Loans (AED bn) are once per deal, and only for the two procedures whose amount is a "
        "verified loan (C10). **Portfolio mortgage registrations** (`is_portfolio_mortgage`: "
        "one loan over several units) are outside the ratio and shown separately, counted "
        "once per deal (C16). Their value is as recorded, not a verified loan amount.",
        "",
        *md_table(
            [
                "Year",
                "Market sales",
                "Ready market sales",
                "Purchase mortgages",
                "Purchase-mortgage share %",
                "New mortgages",
                "New mortgages per 100 sales",
                "Loans AED bn",
                "Portfolio deals",
                "Portfolio lines",
                "Portfolio value AED bn",
            ],
            share,
        ),
        "",
    ]
    path.write_text("\n".join(lines))
    log.info("dq report written to %s in %.0fs", path, time.perf_counter() - t0)
    return path


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
