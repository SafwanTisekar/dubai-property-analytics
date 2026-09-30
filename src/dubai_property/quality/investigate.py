"""Phase 1 investigations on bronze: the evidence behind ``reports/phase1_findings.md``.

Runs a fixed list of SQL checks against the bronze tables and writes every result table
to ``reports/phase1_evidence.md``. The findings document interprets these numbers; this
module makes them reproducible (``make profile`` re-runs it after any reload).

The four questions from docs/08 Phase 1, plus the docs/02 §7 profile figures:

1. The distinct ``procedure_name_en`` values with counts.
2. Whether ``actual_worth`` on mortgage rows is the loan amount. Method: match each
   mortgage row to a *sale of the same unit on the same day* (same date, area, building,
   project, area in sq m, rooms, sub-type; unique on both sides) and look at the ratio
   mortgage value / sale price. A loan shows up as a ratio clustered under the LTV caps
   (0.75-0.80); a property value shows up as a ratio of 1.
3. How multi-property rent contracts repeat amounts, and how much a naive sum inflates.
4. Date formats and invalid dates.

Plus portfolio deals whose single deal value is repeated on every unit line. The bulk
export gives every line its own ``transaction_id``, so such groups are *inferred*: same
group, procedure, date, value and ID-year; ``transaction_id`` sequence numbers close
together (span <= 2 x lines, i.e. registered in one batch); and unit sizes that differ by
more than 10% (identical units can legitimately sell at identical prices; a 822 sq m and
a 1,540 sq m unit with the same "price" cannot).

All work is SQL; only small result tables come back to Python.
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from dubai_property import config, db

log = logging.getLogger(__name__)

REPORT_PATH = config.REPORTS / "phase1_evidence.md"

# Inferred repeated-value groups (see module docstring). Kept as named SQL so the
# findings doc and the Phase 2 dbt flag can use exactly the same definition.
REPEATED_VALUE_GROUP = "lines > 1 and id_span <= 2 * lines and area_ratio > 1.10"


@dataclass(frozen=True)
class Check:
    """One SQL query whose result is rendered as a markdown table."""

    caption: str
    sql: str


@dataclass(frozen=True)
class Section:
    """A group of checks with an explanation, rendered under one heading."""

    title: str
    intro: str
    checks: list[Check]
    setup: list[str] = field(default_factory=list)  # temp tables, run before the checks


SETUP_TXN = [
    # One row per (group, procedure, date, value, ID-year): candidate repeated-value groups.
    """
    create temp table txn_value_groups as
    select trans_group_en as grp, procedure_name_en as procedure, instance_date,
           actual_worth::numeric as worth, split_part(transaction_id, '-', 3) as id_year,
           count(*) as lines,
           max(split_part(transaction_id, '-', 4)::int)
             - min(split_part(transaction_id, '-', 4)::int) + 1 as id_span,
           max(procedure_area::numeric) / nullif(min(procedure_area::numeric), 0) as area_ratio
    from bronze.dld_transactions
    group by 1, 2, 3, 4, 5
    """,
    "analyze txn_value_groups",
]

SETUP_MORTGAGE_MATCH = [
    # A "unit-day key": the same unit registered on the same day in two procedures.
    """
    create temp table txn_keyed as
    select trans_group_en as grp, procedure_id::int as procedure_id,
           procedure_name_en as procedure, left(instance_date, 4) as yr,
           actual_worth::numeric as worth,
           md5(concat_ws('|', instance_date, area_id, building_name_en, project_number,
                         procedure_area, rooms_en, property_sub_type_en, property_type_en)) as k
    from bronze.dld_transactions
    """,
    "analyze txn_keyed",
    """
    create temp table sale_by_key as
    select k, min(worth) as sale_worth, min(procedure) as sale_procedure
    from txn_keyed where grp = 'Sales' and procedure_id in (11, 102, 41)  -- Sell, Sell pre-reg,
    group by k having count(*) = 1                                         -- Delayed Sell
    """,
    """
    create temp table mortgage_by_key as
    select k, min(worth) as loan, min(procedure) as mortgage_procedure, min(yr) as yr
    from txn_keyed where grp = 'Mortgages' and procedure_id in (13, 105, 190)
    group by k having count(*) = 1
    """,
    "analyze sale_by_key",
    "analyze mortgage_by_key",
    """
    create temp table mortgage_pairs as
    select m.*, s.sale_worth, s.sale_procedure, m.loan / nullif(s.sale_worth, 0) as ratio
    from mortgage_by_key m join sale_by_key s using (k)
    """,
]

SETUP_RENT = [
    """
    create temp table rent_contracts as
    select contract_id, count(*) as lines, count(distinct line_number) as distinct_line_numbers,
           max(line_number::int) as max_line_number,
           min(no_of_prop::int) as no_of_prop_min, max(no_of_prop::int) as no_of_prop_max,
           count(distinct annual_amount) as distinct_annual,
           count(distinct contract_amount) as distinct_contract_amount,
           min(annual_amount::numeric) as annual_amount,
           sum(annual_amount::numeric) as annual_amount_line_sum,
           count(distinct nullif(actual_area, '')) as distinct_areas,
           min(left(contract_start_date, 4)) as start_year,
           min(contract_reg_type_en) as reg_type
    from bronze.dld_rent_contracts group by 1
    """,
    "analyze rent_contracts",
]

SECTIONS = [
    Section(
        "1. Procedures (`procedure_name_en`)",
        "All distinct procedure / transaction-group pairs. `procedure_id` is unique per "
        "name, but six lease-to-own and lease-development procedures appear under **both** "
        "Sales and Mortgages.",
        [
            Check(
                "Procedures by transaction group",
                """
                select trans_group_en, procedure_id, procedure_name_en, count(*) as rows,
                       min(left(instance_date, 4)) as first_year,
                       max(left(instance_date, 4)) as last_year
                from bronze.dld_transactions group by 1, 2, 3 order by 1, 4 desc
                """,
            ),
            Check(
                "Transaction groups",
                """
                select trans_group_en, count(*) as rows,
                       round(100.0 * count(*) / sum(count(*)) over (), 1) as pct,
                       count(distinct procedure_name_en) as procedures
                from bronze.dld_transactions group by 1 order by 2 desc
                """,
            ),
            Check(
                "Procedures registered under both Sales and Mortgages: are they the same deal? "
                "(match on date + area + size; value equal or not)",
                """
                with dual as (
                    select trans_group_en as grp, procedure_id, instance_date, area_id,
                           procedure_area, actual_worth
                    from bronze.dld_transactions
                    where procedure_id in ('107', '110', '361', '371', '715', '814')
                ), m_unit as (
                    select distinct procedure_id, instance_date, area_id, procedure_area
                    from dual where grp = 'Mortgages'
                ), m_value as (
                    select distinct procedure_id, instance_date, area_id, procedure_area,
                           actual_worth
                    from dual where grp = 'Mortgages'
                )
                select count(*) filter (where d.grp = 'Sales') as sales_rows,
                  count(*) filter (where d.grp = 'Mortgages') as mortgage_rows,
                  count(*) filter (where d.grp = 'Sales' and mu.procedure_id is not null)
                    as sales_rows_with_same_unit_day_mortgage,
                  count(*) filter (where d.grp = 'Sales' and mv.procedure_id is not null)
                    as of_which_same_value
                from dual d
                left join m_unit mu
                  on (mu.procedure_id, mu.instance_date, mu.area_id, mu.procedure_area)
                   = (d.procedure_id, d.instance_date, d.area_id, d.procedure_area)
                left join m_value mv
                  on (mv.procedure_id, mv.instance_date, mv.area_id, mv.procedure_area,
                      mv.actual_worth)
                   = (d.procedure_id, d.instance_date, d.area_id, d.procedure_area,
                      d.actual_worth)
                """,
            ),
        ],
    ),
    Section(
        "2. Is `actual_worth` on mortgage rows the loan amount?",
        "Mortgage rows matched to a sale of the same unit on the same day (key: date, area, "
        "building, project, sq m, rooms, sub-type; unique on both sides). `ratio` = mortgage "
        "`actual_worth` / sale `actual_worth`.",
        [
            Check(
                "Ratio distribution by procedure pair",
                """
                select mortgage_procedure, sale_procedure, count(*) as pairs,
                  round(percentile_cont(0.10) within group (order by ratio)::numeric, 3) as p10,
                  round(percentile_cont(0.25) within group (order by ratio)::numeric, 3) as p25,
                  round(percentile_cont(0.50) within group (order by ratio)::numeric, 3) as median,
                  round(percentile_cont(0.75) within group (order by ratio)::numeric, 3) as p75,
                  round(percentile_cont(0.90) within group (order by ratio)::numeric, 3) as p90,
                  round(100.0 * avg((ratio between 0.999 and 1.001)::int), 1) as pct_equal,
                  round(100.0 * avg((ratio <= 0.85)::int), 1) as pct_le_0_85,
                  round(100.0 * avg((ratio > 1.001)::int), 1) as pct_above_1
                from mortgage_pairs group by 1, 2 order by 3 desc
                """,
            ),
            Check(
                "Mortgage Registration vs Sell/Delayed Sell: mass at the LTV caps, by year (2010+)",
                """
                select yr, count(*) as pairs,
                  round(percentile_cont(0.5) within group (order by ratio)::numeric, 3) as median,
                  round(100.0 * avg((ratio between 0.745 and 0.755)::int), 1) as pct_at_0_75,
                  round(100.0 * avg((ratio between 0.795 and 0.805)::int), 1) as pct_at_0_80,
                  round(100.0 * avg((ratio between 0.999 and 1.001)::int), 1) as pct_equal
                from mortgage_pairs
                where mortgage_procedure in ('Mortgage Registration', 'Delayed Mortgage')
                  and sale_procedure in ('Sell', 'Delayed Sell') and yr >= '2010'
                group by 1 order by 1
                """,
            ),
            Check(
                "Match coverage",
                """
                select (select count(*) from bronze.dld_transactions
                        where procedure_id in ('13', '105', '190')) as mortgage_rows,
                       (select count(*) from mortgage_by_key) as with_unique_unit_day_key,
                       (select count(*) from mortgage_pairs) as matched_to_a_sale
                """,
            ),
        ],
        setup=SETUP_MORTGAGE_MATCH,
    ),
    Section(
        "2b. Portfolio deals: one deal value repeated on every unit line",
        "Inferred repeated-value groups: `" + REPEATED_VALUE_GROUP + "` (see module "
        "docstring). `overstated` = worth × (lines − 1), i.e. what a naive "
        "`sum(actual_worth)` double-counts. Groups where sizes are within 10% are shown "
        "separately: they may be identical units at identical prices.",
        [
            Check(
                "By transaction group (AED bn)",
                f"""
                select grp,
                  count(*) filter (where {REPEATED_VALUE_GROUP}) as groups,
                  sum(lines) filter (where {REPEATED_VALUE_GROUP}) as lines,
                  round(sum(worth * (lines - 1)) filter (where {REPEATED_VALUE_GROUP}) / 1e9, 1)
                    as overstated_bn,
                  round(sum(worth * lines) / 1e9, 1) as naive_total_bn,
                  round(100 * sum(worth * (lines - 1)) filter (where {REPEATED_VALUE_GROUP})
                    / sum(worth * lines), 1) as pct_of_naive_total,
                  count(*) filter (where lines > 1 and id_span <= 2 * lines
                                   and area_ratio <= 1.10) as similar_size_groups,
                  sum(lines) filter (where lines > 1 and id_span <= 2 * lines
                                     and area_ratio <= 1.10) as similar_size_lines
                from txn_value_groups group by 1 order by 1
                """,
            ),
            Check(
                "Mortgages by procedure (AED bn)",
                f"""
                select procedure, count(*) as groups, sum(lines) as lines,
                       max(lines) as max_lines,
                       round(sum(worth * (lines - 1)) / 1e9, 2) as overstated_bn
                from txn_value_groups where grp = 'Mortgages' and {REPEATED_VALUE_GROUP}
                group by 1 order by 5 desc
                """,
            ),
            Check(
                "Mortgage value by year, naive vs corrected (AED bn, 2010+)",
                f"""
                select left(instance_date, 4) as yr,
                  round(sum(worth * lines) / 1e9, 1) as naive_bn,
                  round(sum(worth * lines - case when {REPEATED_VALUE_GROUP}
                        then worth * (lines - 1) else 0 end) / 1e9, 1) as corrected_bn
                from txn_value_groups where grp = 'Mortgages' and instance_date >= '2010'
                group by 1 order by 1
                """,
            ),
            Check(
                "Example: one Portfolio Mortgage Registration",
                """
                select instance_date, procedure_name_en, area_name_en, procedure_area,
                       actual_worth, meter_sale_price, transaction_id
                from bronze.dld_transactions
                where procedure_id = '43' and instance_date = '2007-08-23'
                order by split_part(transaction_id, '-', 4)::int
                """,
            ),
        ],
        setup=SETUP_TXN,
    ),
    Section(
        "3. Multi-property rent contracts",
        "One row per `contract_id` in a temp table. A contract is multi-line when it has "
        "more than one line.",
        [
            Check(
                "Single vs multi-line contracts",
                """
                select case when lines > 1 then 'multi-line' else 'single-line' end as kind,
                  count(*) as contracts, sum(lines) as lines,
                  count(*) filter (where distinct_line_numbers <> lines) as dup_line_numbers,
                  count(*) filter (where max_line_number <> lines) as line_number_gaps,
                  count(*) filter (where no_of_prop_max <> lines
                                   or no_of_prop_min <> no_of_prop_max) as no_of_prop_ne_lines,
                  count(*) filter (where distinct_annual = 1) as same_annual_amount_every_line,
                  count(*) filter (where distinct_contract_amount = 1)
                    as same_contract_amount_every_line,
                  count(*) filter (where distinct_areas > 1) as unit_area_varies
                from rent_contracts group by 1 order by 1 desc
                """,
            ),
            Check(
                "Inflation of a naive sum of `annual_amount` (AED bn)",
                """
                select round(sum(annual_amount_line_sum) / 1e9, 1) as naive_line_sum_bn,
                  round(sum(annual_amount) / 1e9, 1) as once_per_contract_bn,
                  round(sum(annual_amount_line_sum) / sum(annual_amount), 2) as inflation_x,
                  round(sum(annual_amount_line_sum) filter (where lines > 1) / 1e9, 1)
                    as multi_naive_bn,
                  round(sum(annual_amount) filter (where lines > 1) / 1e9, 1) as multi_once_bn,
                  round(100.0 * sum(annual_amount) filter (where lines > 1)
                    / sum(annual_amount), 1) as multi_share_of_value_pct
                from rent_contracts
                """,
            ),
            Check(
                "Contracts by number of lines",
                """
                select case when lines = 1 then '1' when lines <= 5 then '2-5'
                            when lines <= 20 then '6-20' when lines <= 100 then '21-100'
                            else '100+' end as lines_bucket,
                  count(*) as contracts, sum(lines) as lines,
                  round(100.0 * avg((distinct_annual = 1)::int), 1) as pct_same_amount
                from rent_contracts group by 1 order by min(lines)
                """,
            ),
            Check(
                "Multi-line share by contract start year and New/Renew (2015+)",
                """
                select start_year, reg_type, count(*) as contracts,
                  round(100.0 * avg((lines > 1)::int), 2) as pct_multi_line_contracts,
                  sum(lines) filter (where lines > 1) as lines_in_multi
                from rent_contracts where start_year between '2015' and '2026'
                group by 1, 2 order by 1, 2
                """,
            ),
            Check(
                "Example: a 4-unit contract",
                """
                select contract_id, line_number, no_of_prop, annual_amount, contract_amount,
                       actual_area, ejari_property_sub_type_en, contract_start_date
                from bronze.dld_rent_contracts where contract_id = 'CNT100148436'
                order by line_number::int
                """,
            ),
        ],
        setup=SETUP_RENT,
    ),
    Section(
        "4. Date formats",
        "Each value's shape with digits replaced by 9 and letters by a.",
        [
            Check(
                "Shapes of every date column",
                """
                select 'dld_transactions.instance_date' as col,
                       regexp_replace(instance_date, '[0-9]', '9', 'g') as shape, count(*),
                       min(instance_date), max(instance_date)
                from bronze.dld_transactions group by 1, 2
                union all
                select 'dld_transactions.load_timestamp',
                       regexp_replace(regexp_replace(load_timestamp, '[0-9]', '9', 'g'),
                                      '[A-Za-z]', 'a', 'g'), count(*),
                       min(load_timestamp), max(load_timestamp)
                from bronze.dld_transactions group by 1, 2
                union all
                select 'dld_rent_contracts.contract_start_date',
                       regexp_replace(contract_start_date, '[0-9]', '9', 'g'), count(*),
                       min(contract_start_date), max(contract_start_date)
                from bronze.dld_rent_contracts group by 1, 2
                union all
                select 'dld_rent_contracts.contract_end_date',
                       regexp_replace(contract_end_date, '[0-9]', '9', 'g'), count(*),
                       min(contract_end_date), max(contract_end_date)
                from bronze.dld_rent_contracts group by 1, 2
                union all
                select 'rates_fedfunds.observation_date',
                       regexp_replace(observation_date, '[0-9]', '9', 'g'), count(*),
                       min(observation_date), max(observation_date)
                from bronze.rates_fedfunds group by 1, 2
                union all
                select 'rates_brent.observation_date',
                       regexp_replace(observation_date, '[0-9]', '9', 'g'), count(*),
                       min(observation_date), max(observation_date)
                from bronze.rates_brent group by 1, 2
                """,
            ),
            Check(
                "`instance_date` by era",
                """
                select case when instance_date < '1900' then '1 before 1900 (Hijri)'
                            when instance_date < '2004' then '2 1900-2003'
                            when instance_date <= '2026-09-29' then '3 2004 to snapshot'
                            else '4 after snapshot' end as era,
                       count(*), min(instance_date), max(instance_date)
                from bronze.dld_transactions group by 1 order by 1
                """,
            ),
            Check(
                "The Hijri-dated rows (year in `transaction_id` for comparison)",
                """
                select instance_date, transaction_id, split_part(transaction_id, '-', 3)
                       as id_year, procedure_name_en, actual_worth
                from bronze.dld_transactions where instance_date < '1900' order by 1
                """,
            ),
            Check(
                "`transaction_id` year minus `instance_date` year",
                """
                select split_part(transaction_id, '-', 3)::int - left(instance_date, 4)::int
                       as id_year_minus_date_year, count(*)
                from bronze.dld_transactions group by 1 order by 2 desc limit 10
                """,
            ),
            Check(
                "Rent contract dates",
                """
                select count(*) filter (where contract_start_date < '2004') as start_pre_2004,
                  count(*) filter (where contract_start_date > '2026-09-30')
                    as start_after_snapshot,
                  count(*) filter (where contract_end_date < contract_start_date)
                    as end_before_start,
                  count(*) filter (where contract_end_date > '2040') as end_after_2040,
                  max(contract_end_date) as max_end
                from bronze.dld_rent_contracts
                """,
            ),
            Check(
                "FRED missing values (empty value field)",
                """
                select 'fedfunds' as series, count(*) filter (where fedfunds = '') as blank,
                       count(*) as rows from bronze.rates_fedfunds
                union all
                select 'brent', count(*) filter (where dcoilbrenteu = ''), count(*)
                from bronze.rates_brent
                """,
            ),
        ],
    ),
    Section(
        "5. Encoding: Arabic columns",
        "Share of rows whose `_ar` columns contain Arabic script (U+0600–U+06FF), and rows "
        "with typical mojibake (`Ø`, `Ù`) or the replacement character U+FFFD.",
        [
            Check(
                "Arabic integrity",
                """
                select 'dld_transactions' as tbl, count(*) as rows,
                  count(*) filter (where area_name_ar ~ '[\u0600-\u06ff]') as area_ar_arabic,
                  count(*) filter (where procedure_name_ar ~ '[\u0600-\u06ff]')
                    as procedure_ar_arabic,
                  count(*) filter (where concat(area_name_ar, procedure_name_ar, project_name_ar,
                                   building_name_ar) ~ '(\ufffd|Ø|Ù)') as mojibake_rows
                from bronze.dld_transactions
                union all
                select 'dld_rent_contracts', count(*),
                  count(*) filter (where area_name_ar ~ '[\u0600-\u06ff]'),
                  count(*) filter (where contract_reg_type_ar ~ '[\u0600-\u06ff]'),
                  count(*) filter (where concat(area_name_ar, project_name_ar, master_project_ar)
                                   ~ '(\ufffd|Ø|Ù)')
                from bronze.dld_rent_contracts
                """,
            ),
            Check(
                "`property_usage`: EN/AR labels swapped for one category",
                """
                select property_usage_en, property_usage_ar, count(*) as rows
                from bronze.dld_transactions group by 1, 2 order by 3 desc
                """,
            ),
        ],
    ),
    Section(
        "6. docs/02 §7 figures",
        "Sales = `trans_group_en = 'Sales'` (all sale procedures, before the Phase 2 "
        'market-sale filter). Snapshot runs to 2026-09-25, so "last 12 months" is '
        "2025-09-26 → 2026-09-25 and the last full year is 2025.",
        [
            Check(
                "Transactions: rows and valid date range (2004+)",
                """
                select count(*) as rows, min(instance_date) filter (where instance_date >= '2004')
                       as first_2004plus, max(instance_date) as last,
                       count(*) filter (where instance_date < '2004') as pre_2004_rows,
                       count(distinct area_id) as distinct_area_ids
                from bronze.dld_transactions
                """,
            ),
            Check(
                "Off-plan share of sales, last 12 months",
                """
                select count(*) as sales_rows,
                  count(*) filter (where reg_type_en = 'Off-Plan Properties') as offplan_rows,
                  round(100.0 * avg((reg_type_en = 'Off-Plan Properties')::int), 1)
                    as offplan_pct_rows,
                  round(100.0 * sum(actual_worth::numeric)
                    filter (where reg_type_en = 'Off-Plan Properties')
                    / sum(actual_worth::numeric), 1) as offplan_pct_value
                from bronze.dld_transactions
                where trans_group_en = 'Sales'
                  and instance_date between '2025-09-26' and '2026-09-25'
                """,
            ),
            Check(
                "Sales value, full year 2025 (AED bn)",
                f"""
                select count(*) as sales_rows,
                  round(sum(actual_worth::numeric) / 1e9, 1) as naive_sum_bn,
                  round(sum(actual_worth::numeric) filter
                    (where procedure_name_en in ('Sell', 'Sell - Pre registration',
                     'Delayed Sell')) / 1e9, 1) as sell_procedures_bn,
                  (select round(sum(worth * (lines - 1)) / 1e9, 1) from txn_value_groups
                   where grp = 'Sales' and instance_date like '2025%'
                     and {REPEATED_VALUE_GROUP}) as repeated_value_overstatement_bn
                from bronze.dld_transactions
                where trans_group_en = 'Sales' and instance_date like '2025%'
                """,
            ),
            Check(
                "Rent lines, contracts and areas",
                """
                select (select count(*) from bronze.dld_rent_contracts) as lines,
                  (select count(*) from rent_contracts) as contracts,
                  (select count(distinct area_id) from bronze.dld_rent_contracts)
                    as distinct_area_ids,
                  (select count(distinct area_id) from (
                     select area_id from bronze.dld_transactions union
                     select area_id from bronze.dld_rent_contracts) u) as area_ids_either_table
                """,
            ),
        ],
        setup=SETUP_TXN + SETUP_RENT,
    ),
]


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, int | Decimal) and value == int(value):
        return f"{int(value):,}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(columns: list[str], rows: list[tuple]) -> list[str]:
    out = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    out += ["| " + " | ".join(_cell(v) for v in row) + " |" for row in rows]
    return out


def run(path: Path = REPORT_PATH) -> Path:
    """Run every section and write the evidence report."""
    lines = [
        "# Phase 1 evidence: bronze investigations",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `quality/investigate.py`. Raw "
        "query results; interpretation is in [phase1_findings.md](phase1_findings.md).",
    ]
    t_all = time.perf_counter()
    with db.connect() as conn:
        conn.execute("set work_mem = '1GB'")
        created: set[str] = set()
        for section in SECTIONS:
            t0 = time.perf_counter()
            for stmt in section.setup:
                name = stmt.split()[3] if stmt.strip().startswith("create temp") else None
                if name in created:
                    continue  # temp tables are shared between sections
                conn.execute(stmt)
                if name:
                    created.add(name)
            lines += ["", f"## {section.title}", "", section.intro]
            for check in section.checks:
                cur = conn.execute(check.sql)
                columns = [d.name for d in cur.description or []]
                lines += ["", f"**{check.caption}**", "", *_table(columns, cur.fetchall())]
            log.info("%s (%.0fs)", section.title, time.perf_counter() - t0)
        conn.rollback()
    path.write_text("\n".join(lines) + "\n")
    log.info("evidence written to %s in %.0fs", path, time.perf_counter() - t_all)
    return path


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
