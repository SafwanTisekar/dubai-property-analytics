"""KPI reconciliation: every pre-ML KPI in docs/01 §4, computed from silver and from rpt.

Writes ``reports/kpi_reconciliation.md`` (``make kpi``; ``make dbt`` runs it). These are
the numbers the Power BI cards must match before publishing (docs/06 §3).

Each KPI is computed **independently** twice:

* **Silver** (canonical): straight from ``silver.int_market_sales``, ``int_mortgages`` and
  ``int_rent_contracts`` with the docs/01 §4 definitions, dated from 2004 to the data
  snapshot date (``silver.int_data_snapshot``, the latest transaction date). It shares no
  SQL with gold, so a bug in a mart or an rpt view shows up as a mismatch.
* **rpt** (what Power BI imports): ``rpt.transactions`` and ``rpt.area_month`` for sales
  and financing, ``rpt.rent_month`` for rents.

They must agree at three grains (all time, each year, each month). Counts must match
exactly. rpt rounds AED to whole dirhams per row, so an AED total may differ by up to
0.5 AED per row summed; areas are rounded to 0.01 sq m; a median over rounded prices may
differ by up to 1 AED. Ratios (shares, AED per sq m) are derived from the checked totals.

Area-weighted AED per sq m (Σ AED / Σ sq m) is only meaningful within a property class,
so the headline figures cover **residential apartments and villas / townhouses** with an
area within the class cap (owner, 2026-09-30). A sanity check requires the apartment
area-weighted price to stay within ±40% of the apartment median in every year from 2010.

The price index, YoY growth, yields, AVM accuracy, drawdown, negative equity and developer
concentration come from Phase 4 models and are listed as pending.
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg

from dubai_property import config, db
from dubai_property.quality.dq_report import md_table

log = logging.getLogger(__name__)

REPORT_PATH = config.REPORTS / "kpi_reconciliation.md"

# Apartment sanity check: area-weighted vs median AED per sq m, every year from 2010.
DIVERGENCE_FROM_YEAR = 2010
DIVERGENCE_TOLERANCE = 0.40
# It needs the full register: the CI fixtures and the 2% sample have a handful of
# apartment sales a year, so their medians and ratios are noise. Below this many
# transaction lines in scope the check is reported as not applicable, not failed.
DIVERGENCE_MIN_LINES = 100_000

# metric -> kind; the kind sets the tolerance (see ``tolerance``).
METRICS: dict[str, str] = {
    "market_sales": "count",
    "ready_sales": "count",
    "purchase_mortgages": "count",
    "market_value": "aed",
    "offplan_sales": "count",
    "offplan_value": "aed",
    "clean_sales": "count",
    "median_ppsqm": "median",
    "aw_value": "aed",
    "aw_area": "area",
    "apt_median": "median",
    "apt_aw_value": "aed",
    "apt_aw_area": "area",
    "new_mortgages": "count",
    "portfolio_deals": "count",
    "portfolio_value": "aed",
    "market_rents": "count",
    "rent_aw_value": "aed",
    "rent_aw_area": "area",
}

_HOMES = ", ".join(str(k) for k in config.RESIDENTIAL_HOMES_KEYS)
_APT = config.RESIDENTIAL_APARTMENT_KEY
# The class caps as SQL (mirrors the dbt macro class_area_cap; pinned by tests/test_config).
_CAP = (
    "case property_class_id "
    + " ".join(f"when {k} then {v}" for k, v in config.AREA_CAP_SQM.items())
    + f" else {config.AREA_CAP_OTHER_SQM} end"
)

# One SELECT list per source. `period` is 'all', 'YYYY' or 'YYYY-MM' (grouping sets), and
# `_rows` counts the rows summed, which bounds the rounding error of an rpt total.
_PERIOD = """
    case
        when grouping(yr) = 1 and grouping(mon) = 1 then 'all'
        when grouping(mon) = 1 then to_char(yr, 'YYYY')
        else to_char(mon, 'YYYY-MM')
    end as period
"""
_GROUPING = "group by grouping sets ((), (yr), (mon))"

SNAPSHOT_SQL = "select data_snapshot_date from silver.int_data_snapshot"

# Purchase mortgages (docs/01 §4), re-derived from silver with a different formulation
# from dbt's int_purchase_mortgage_pairs (window counts over the unit key instead of a
# GROUP BY), so an error in either shows up as a mismatch.
_PM_KEY = """md5(concat_ws('|', txn_date, coalesce(area_id, -1), coalesce(building_name, ''),
                  coalesce(project_number, -1), area_sqm, coalesce(rooms_en, ''),
                  coalesce(property_type, ''), coalesce(property_sub_type, '')))"""

SILVER_SALES_SQL = f"""
with pm_legs as (
    select 'sale' as side, transaction_id, procedure_name, is_repeated_deal_value,
           {_PM_KEY} as k
    from silver.int_market_sales
    where procedure_name in ('Sell', 'Delayed Sell') and is_market_sale and not is_offplan
      and txn_date is not null and area_sqm is not null
    union all
    select 'mortgage', transaction_id, procedure_name, is_repeated_deal_value, {_PM_KEY}
    from silver.int_mortgages
    where procedure_name in ('Mortgage Registration', 'Delayed Mortgage')
      and txn_date is not null and area_sqm is not null
),
pm_counted as (
    select *,
           count(*) filter (where side = 'sale') over w as sales_on_key,
           count(*) filter (where side = 'mortgage') over w as mortgages_on_key,
           max(procedure_name) filter (where side = 'mortgage') over w as mortgage_proc,
           bool_or(is_repeated_deal_value) over w as any_repeated
    from pm_legs
    window w as (partition by k)
),
pm_sales as (
    select transaction_id
    from pm_counted
    where side = 'sale' and sales_on_key = 1 and mortgages_on_key = 1 and not any_repeated
      and (mortgage_proc, procedure_name) in (('Mortgage Registration', 'Sell'),
                                              ('Delayed Mortgage', 'Delayed Sell'))
),
lines as (
    select txn_date, is_market_sale, is_clean_market_sale, is_offplan,
           actual_worth_once_aed as aed, price_per_sqm_aed as ppsqm, area_sqm,
           false as is_new_mortgage, false as is_portfolio_mortgage,
           null::text as deal_group_id, null::numeric as portfolio_value,
           property_usage, property_type, property_sub_type,
           transaction_id in (select transaction_id from pm_sales) as has_purchase_mortgage
    from silver.int_market_sales
    union all
    select txn_date, false, false, is_offplan, actual_worth_once_aed, null, area_sqm,
           is_new_mortgage, is_portfolio_mortgage, deal_group_id,
           portfolio_mortgage_value_once_aed, property_usage, property_type, property_sub_type,
           false
    from silver.int_mortgages
),
scoped as (
    select l.*, k.property_type_key, k.property_class_id,
           date_trunc('year', txn_date)::date as yr, date_trunc('month', txn_date)::date as mon
    from lines as l
    join silver.int_property_type_lookup as k
        on k.source = 'transactions'
        and k.property_usage_join = coalesce(l.property_usage, '')
        and k.property_type_join = coalesce(l.property_type, '')
        and k.property_sub_type_join = coalesce(l.property_sub_type, '')
    where txn_date between %(start)s and %(end)s
),
flagged as (
    select *,
           is_clean_market_sale and coalesce(area_sqm <= {_CAP}, true) as is_aw
    from scoped
)
select {_PERIOD},
    count(*) as _rows,
    count(*) filter (where is_market_sale) as market_sales,
    count(*) filter (where is_market_sale and not is_offplan) as ready_sales,
    count(*) filter (where has_purchase_mortgage) as purchase_mortgages,
    coalesce(sum(aed) filter (where is_market_sale), 0) as market_value,
    count(*) filter (where is_market_sale and is_offplan) as offplan_sales,
    coalesce(sum(aed) filter (where is_market_sale and is_offplan), 0) as offplan_value,
    count(*) filter (where is_clean_market_sale) as clean_sales,
    percentile_cont(0.5) within group (order by ppsqm)
        filter (where is_clean_market_sale) as median_ppsqm,
    coalesce(sum(aed) filter (where is_aw and property_type_key in ({_HOMES})), 0) as aw_value,
    coalesce(sum(area_sqm) filter (where is_aw and property_type_key in ({_HOMES})), 0)
        as aw_area,
    percentile_cont(0.5) within group (order by ppsqm)
        filter (where is_clean_market_sale and property_type_key = {_APT}) as apt_median,
    coalesce(sum(aed) filter (where is_aw and property_type_key = {_APT}), 0) as apt_aw_value,
    coalesce(sum(area_sqm) filter (where is_aw and property_type_key = {_APT}), 0) as apt_aw_area,
    count(*) filter (where is_new_mortgage) as new_mortgages,
    count(distinct deal_group_id) filter (where is_portfolio_mortgage) as portfolio_deals,
    coalesce(sum(portfolio_value), 0) as portfolio_value
from flagged
{_GROUPING}
"""

RPT_TRANSACTIONS_SQL = f"""
with scoped as (
    select *, date_trunc('year', "Date")::date as yr, date_trunc('month', "Date")::date as mon,
           "Is Clean Market Sale" and not "Area Above Class Cap" as is_aw
    from rpt.transactions
)
select {_PERIOD},
    count(*) as _rows,
    count(*) filter (where "Is Market Sale") as market_sales,
    count(*) filter (where "Is Market Sale" and not "Is Off-Plan") as ready_sales,
    count(*) filter (where "Has Purchase Mortgage") as purchase_mortgages,
    coalesce(sum("AED Counted Once") filter (where "Is Market Sale"), 0) as market_value,
    count(*) filter (where "Is Market Sale" and "Is Off-Plan") as offplan_sales,
    coalesce(sum("AED Counted Once") filter (where "Is Market Sale" and "Is Off-Plan"), 0)
        as offplan_value,
    count(*) filter (where "Is Clean Market Sale") as clean_sales,
    percentile_cont(0.5) within group (order by "Price per Sq M AED")
        filter (where "Is Clean Market Sale") as median_ppsqm,
    coalesce(sum("AED Counted Once")
        filter (where is_aw and "Property Type Key" in ({_HOMES})), 0) as aw_value,
    coalesce(sum("Area Sq M") filter (where is_aw and "Property Type Key" in ({_HOMES})), 0)
        as aw_area,
    percentile_cont(0.5) within group (order by "Price per Sq M AED")
        filter (where "Is Clean Market Sale" and "Property Type Key" = {_APT}) as apt_median,
    coalesce(sum("AED Counted Once") filter (where is_aw and "Property Type Key" = {_APT}), 0)
        as apt_aw_value,
    coalesce(sum("Area Sq M") filter (where is_aw and "Property Type Key" = {_APT}), 0)
        as apt_aw_area,
    count(*) filter (where "Is New Mortgage") as new_mortgages,
    count(*) filter (where "Is Portfolio Mortgage" and "Is Deal Lead") as portfolio_deals,
    coalesce(sum("Portfolio Mortgage Value AED"), 0) as portfolio_value
from scoped
{_GROUPING}
"""

RPT_AREA_MONTH_SQL = f"""
with scoped as (
    select *, date_trunc('year', "Month")::date as yr, "Month" as mon
    from rpt.area_month
)
select {_PERIOD},
    count(*) as _rows,
    sum("Market Sales") as market_sales,
    coalesce(sum("Market Sales") filter (where not "Is Off-Plan"), 0) as ready_sales,
    sum("Purchase Mortgages") as purchase_mortgages,
    sum("Market Sales Value AED") as market_value,
    coalesce(sum("Market Sales") filter (where "Is Off-Plan"), 0) as offplan_sales,
    coalesce(sum("Market Sales Value AED") filter (where "Is Off-Plan"), 0) as offplan_value,
    sum("Clean Sales") as clean_sales,
    coalesce(sum("Clean Sales Value AED") filter (where "Property Type Key" in ({_HOMES})), 0)
        as aw_value,
    coalesce(sum("Clean Sales Area Sq M") filter (where "Property Type Key" in ({_HOMES})), 0)
        as aw_area,
    coalesce(sum("Clean Sales Value AED") filter (where "Property Type Key" = {_APT}), 0)
        as apt_aw_value,
    coalesce(sum("Clean Sales Area Sq M") filter (where "Property Type Key" = {_APT}), 0)
        as apt_aw_area,
    sum("New Mortgages") as new_mortgages,
    sum("Portfolio Mortgage Deals") as portfolio_deals,
    sum("Portfolio Mortgage Value AED") as portfolio_value
from scoped
{_GROUPING}
"""

SILVER_RENTS_SQL = f"""
with scoped as (
    select r.*, k.property_type_key, date_trunc('year', start_date)::date as yr,
           date_trunc('month', start_date)::date as mon
    from silver.int_rent_contracts as r
    join silver.int_property_type_lookup as k
        on k.source = 'rents'
        and k.property_usage_join = coalesce(r.property_usage, '')
        and k.property_type_join = coalesce(r.property_type, '')
        and k.property_sub_type_join = coalesce(r.property_sub_type, '')
    where not r.is_date_invalid and r.start_date between %(start)s and %(end)s
)
select {_PERIOD},
    count(*) as _rows,
    count(*) filter (where is_market_rent) as market_rents,
    coalesce(sum(annual_rent_contract_aed) filter (
        where is_market_rent and rent_per_sqm_aed is not null
            and property_type_key in ({_HOMES})
    ), 0) as rent_aw_value,
    coalesce(sum(area_sqm) filter (
        where is_market_rent and rent_per_sqm_aed is not null
            and property_type_key in ({_HOMES})
    ), 0) as rent_aw_area
from scoped
{_GROUPING}
"""

RPT_RENT_MONTH_SQL = f"""
with scoped as (
    select *, date_trunc('year', "Month")::date as yr, "Month" as mon
    from rpt.rent_month
)
select {_PERIOD},
    count(*) as _rows,
    sum("Market Rent Contracts") as market_rents,
    coalesce(sum("Comparable Rent with Area AED")
        filter (where "Is New Contract" and "Property Type Key" in ({_HOMES})), 0)
        as rent_aw_value,
    coalesce(sum("Comparable Area Sq M")
        filter (where "Is New Contract" and "Property Type Key" in ({_HOMES})), 0)
        as rent_aw_area
from scoped
{_GROUPING}
"""

Table = dict[str, dict[str, Any]]  # period -> metric -> value


@dataclass(frozen=True)
class Mismatch:
    """One KPI input that differs between silver and an rpt view beyond tolerance."""

    source: str
    period: str
    metric: str
    silver: Any
    other: Any
    tolerance: float


def tolerance(kind: str, rows: int) -> float:
    """Largest difference rounding in rpt can explain for a total over ``rows`` rows.

    Args:
        kind: ``count`` (exact), ``aed`` (rounded to whole AED per row), ``area`` (rounded
            to 0.01 sq m per row) or ``median`` (a median of whole-AED prices).
        rows: Rows summed in the rpt view for this period.
    """
    if kind == "count":
        return 0.0
    if kind == "aed":
        return 0.5 * rows
    if kind == "area":
        return 0.005 * rows
    if kind == "median":
        return 1.0
    raise ValueError(f"unknown metric kind: {kind}")


def compare(source: str, silver: Table, other: Table) -> list[Mismatch]:
    """Every metric ``other`` provides, checked against silver in every period.

    A period present in only one of the two tables is a mismatch (a whole month missing
    from an rpt view would otherwise pass unnoticed).
    """
    out = []
    for period in sorted(silver.keys() | other.keys()):
        s_row, o_row = silver.get(period), other.get(period)
        if s_row is None or o_row is None:
            out.append(Mismatch(source, period, "period", s_row is not None, o_row is not None, 0))
            continue
        for metric, kind in METRICS.items():
            if metric not in o_row:
                continue
            s_val, o_val = s_row.get(metric), o_row[metric]
            tol = tolerance(kind, int(o_row["_rows"]))
            if s_val is None or o_val is None:
                ok = s_val is None and o_val is None
            else:
                ok = abs(float(s_val) - float(o_val)) <= tol + 1e-9
            if not ok:
                out.append(Mismatch(source, period, metric, s_val, o_val, tol))
    return out


def _ratio(num: Any, den: Any) -> float | None:
    return float(num) / float(den) if num is not None and den else None


def derive(row: dict[str, Any]) -> dict[str, float | None]:
    """The docs/01 §4 KPIs from one period's base metrics."""
    new, sales = row.get("new_mortgages"), row.get("market_sales") or 0
    return {
        # Headline: matched purchase mortgages / ready market sales (a lower bound).
        "purchase_mortgage_share": _ratio(row.get("purchase_mortgages"), row.get("ready_sales")),
        # Secondary: new mortgages (incl. refinancing) per 100 market sales.
        "new_mortgages_per_100": None if new is None or not sales else 100 * float(new) / sales,
        "offplan_share_count": _ratio(row.get("offplan_sales"), sales),
        "offplan_share_value": _ratio(row.get("offplan_value"), row.get("market_value")),
        "aw_ppsqm": _ratio(row.get("aw_value"), row.get("aw_area")),
        "apt_aw_ppsqm": _ratio(row.get("apt_aw_value"), row.get("apt_aw_area")),
        "rent_aw_sqm": _ratio(row.get("rent_aw_value"), row.get("rent_aw_area")),
    }


def apartment_divergence(
    silver: Table,
    from_year: int = DIVERGENCE_FROM_YEAR,
    limit: float = DIVERGENCE_TOLERANCE,
) -> list[tuple[str, float | None, float | None, float | None]]:
    """Years whose apartment area-weighted AED/sq m is more than ``limit`` off the median.

    Returns ``(year, median, area_weighted, ratio)`` per failing year. A year with no
    apartment sales fails too: the check can't pass on missing data.
    """
    bad = []
    for period, row in sorted(silver.items()):
        if len(period) != 4 or int(period) < from_year:
            continue
        median, aw = row.get("apt_median"), derive(row)["apt_aw_ppsqm"]
        ratio = aw / float(median) if aw is not None and median else None
        if ratio is None or abs(ratio - 1) > limit:
            bad.append((period, median, aw, ratio))
    return bad


def divergence_applies(silver: Table) -> bool:
    """True when the register is large enough for the apartment sanity check."""
    return int(silver.get("all", {}).get("_rows") or 0) >= DIVERGENCE_MIN_LINES


def divergence_failures(
    silver: Table,
) -> list[tuple[str, float | None, float | None, float | None]]:
    """``apartment_divergence`` where the check applies; nothing on small data."""
    return apartment_divergence(silver) if divergence_applies(silver) else []


def fetch(conn: psycopg.Connection, sql: str, start: date, end: date) -> Table:
    """Run one source query; return ``{period: {metric: value}}``."""
    cur = conn.execute(sql, {"start": start, "end": end})
    names = [d.name for d in cur.description]
    return {row[0]: dict(zip(names[1:], row[1:], strict=True)) for row in cur.fetchall()}


def rpt_available(conn: psycopg.Connection) -> bool:
    """True once ``make dbt`` has built the rpt views this module reads."""
    (n,) = conn.execute(
        "select count(*) from pg_views where schemaname = 'rpt'"
        " and viewname in ('transactions', 'area_month', 'rent_month')"
    ).fetchone()
    return n == 3


@dataclass
class Result:
    """Silver tables (canonical values), every mismatch found, and the snapshot date."""

    database: str
    snapshot: date
    silver: Table
    checks: dict[str, int]
    mismatches: list[Mismatch]


def compute(conn: psycopg.Connection) -> Result:
    """Query every source and compare each rpt view with silver."""
    conn.execute("set work_mem = '512MB'")
    (database,) = conn.execute("select current_database()").fetchone()
    (snapshot,) = conn.execute(SNAPSHOT_SQL).fetchone()
    start = config.REPORT_SCOPE_START
    silver_sales = fetch(conn, SILVER_SALES_SQL, start, snapshot)
    silver_rents = fetch(conn, SILVER_RENTS_SQL, start, snapshot)
    others = {
        "rpt.transactions": (silver_sales, fetch(conn, RPT_TRANSACTIONS_SQL, start, snapshot)),
        "rpt.area_month": (silver_sales, fetch(conn, RPT_AREA_MONTH_SQL, start, snapshot)),
        "rpt.rent_month": (silver_rents, fetch(conn, RPT_RENT_MONTH_SQL, start, snapshot)),
    }
    conn.rollback()
    mismatches, checks = [], {}
    for source, (silver, other) in others.items():
        mismatches += compare(source, silver, other)
        checks[source] = sum(1 for row in other.values() for metric in METRICS if metric in row)
    merged = {
        p: {**silver_sales.get(p, {}), **silver_rents.get(p, {})}
        for p in silver_sales.keys() | silver_rents.keys()
    }
    return Result(database, snapshot, merged, checks, mismatches)


# --- Rendering ------------------------------------------------------------------------


def _pct(x: float | None) -> str | None:
    return None if x is None else f"{100 * x:.1f}"


def _bn(x: Any) -> str | None:
    return None if x is None else f"{float(x) / 1e9:,.1f}"


def _aed(x: Any) -> int | None:
    return None if x is None else round(Decimal(str(x)))


def kpi_rows(silver: Table, periods: list[str]) -> list[tuple]:
    """One report row per period: base metrics and the derived KPIs."""
    rows = []
    for p in periods:
        r = silver.get(p, {})
        d = derive(r)
        rows.append(
            (
                p,
                r.get("market_sales"),
                _bn(r.get("market_value")),
                _aed(r.get("median_ppsqm")),
                _aed(d["aw_ppsqm"]),
                r.get("ready_sales"),
                r.get("purchase_mortgages"),
                _pct(d["purchase_mortgage_share"]),
                r.get("new_mortgages"),
                None if d["new_mortgages_per_100"] is None else f"{d['new_mortgages_per_100']:.1f}",
                _pct(d["offplan_share_count"]),
                _pct(d["offplan_share_value"]),
                r.get("portfolio_deals"),
                _bn(r.get("portfolio_value")),
                r.get("market_rents"),
                _aed(d["rent_aw_sqm"]),
            )
        )
    return rows


COLUMNS = [
    "Period",
    "Market sales",
    "Market sales AED bn",
    "Median AED / sq m (all clean sales)",
    "Area-weighted AED / sq m (res. apartments + villas)",
    "Ready market sales",
    "Purchase mortgages (matched)",
    "Purchase-mortgage share of ready sales %",
    "New mortgages",
    "New mortgages per 100 market sales",
    "Off-plan share % (count)",
    "Off-plan share % (value)",
    "Portfolio mortgage deals",
    "Portfolio value AED bn",
    "New market rents",
    "Area-weighted new rent AED / sq m (res. apartments + villas)",
]

PENDING = [
    ("Price index", "Phase 4a: hedonic time-dummy index, Jan 2019 = 100 (docs/05 §2)"),
    ("YoY price growth", "Phase 4a: from the index"),
    ("Gross rental yield", "Phase 4a: agg_yield_quarter with the min-n rule (docs/05 §3)"),
    ("AVM accuracy (MdAPE, ±10% / ±20%)", "Phase 4b (docs/05 §1)"),
    ("Max drawdown", "Phase 4a: from the index"),
    ("Negative-equity share", "Phase 4c: stress grid (docs/05 §4)"),
    ("Developer concentration (HHI)", "Stretch: needs the DLD projects file (deferred)"),
]


def render(result: Result) -> str:
    """The markdown report."""
    years = sorted(p for p in result.silver if len(p) == 4)
    months = sorted(p for p in result.silver if len(p) == 7)[-12:]
    applies = divergence_applies(result.silver)
    divergence = divergence_failures(result.silver)
    failed = len(result.mismatches) + len(divergence)
    status = "**All checks pass.**" if not failed else f"**{failed} failed check(s)**: see §4-5."
    checks = [
        (src, n, sum(m.source == src for m in result.mismatches))
        for src, n in result.checks.items()
    ]
    apt_rows = []
    for p in years:
        r = result.silver[p]
        median, aw = r.get("apt_median"), derive(r)["apt_aw_ppsqm"]
        ratio = aw / float(median) if aw is not None and median else None
        checked = applies and int(p) >= DIVERGENCE_FROM_YEAR
        ok = ratio is not None and abs(ratio - 1) <= DIVERGENCE_TOLERANCE
        apt_rows.append(
            (p, _aed(median), _aed(aw), _pct(ratio), ("pass" if ok else "FAIL") if checked else "")
        )
    lines = [
        "# KPI reconciliation",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `quality/kpi_reconciliation.py` "
        f"from database `{result.database}`. Regenerate with `make kpi` (after `make dbt`); "
        "`tests/test_kpi_reconciliation.py` fails if any check below fails.",
        "",
        "These are the numbers the Power BI cards must match (docs/06 §3). Every KPI in "
        "docs/01 §4 that exists before the models is computed from silver (canonical, below) "
        "and again from the rpt views Power BI imports, at three grains (all time, year, "
        f"month). **Data snapshot: {result.snapshot}** (the latest transaction date; "
        f'`rpt.report_info` "Data As Of"). Scope: {config.REPORT_SCOPE_START} to the '
        f"snapshot; rent contracts starting after it are excluded. {status}",
        "",
        "Definitions (docs/01 §4): **market sales** = `is_market_sale` lines, AED counted once "
        "per deal (C16); **median AED per sq m** = all clean market sales "
        "(`is_clean_market_sale`); **area-weighted AED per sq m** = Σ AED / Σ sq m over clean "
        "sales of residential apartments and villas / townhouses whose area is within the "
        "class cap (1,000 / 3,000 sq m), because across property classes it would mix land, "
        "buildings and units; **purchase-mortgage share of ready sales** = ready market "
        "sales matched to a same-day purchase mortgage of the same unit "
        "(`has_purchase_mortgage`, a lower bound) / ready market sales; **new mortgages per "
        "100 market sales** = individual new mortgages (incl. refinancing) x 100 / market "
        "sales, a secondary indicator; portfolio mortgages are outside both, counted once "
        "per deal; "
        "**off-plan share** = off-plan market sales / market sales; **new market rents** = "
        "`is_market_rent` (new, single-line, comparable, started by the snapshot); "
        "area-weighted rent = Σ annual rent / Σ sq m over new market rents of residential "
        "apartments and villas with a plausible area (C21 class caps).",
        "",
        "## 1. All time",
        "",
        *md_table(COLUMNS, kpi_rows(result.silver, ["all"])),
        "",
        "## 2. By year",
        "",
        *md_table(COLUMNS, kpi_rows(result.silver, years)),
        "",
        "## 3. Last 12 months",
        "",
        f"The 12 months to the snapshot ({result.snapshot}). The snapshot month is partial.",
        "",
        *md_table(COLUMNS, kpi_rows(result.silver, months)),
        "",
        "## 4. Checks: silver vs rpt",
        "",
        "Counts exact; AED within 0.5 AED per row summed and areas within 0.01 sq m per row "
        "(rpt rounds each row); medians within 1 AED. `rpt.area_month` has no median (cell "
        "medians can't be combined), and `rpt.rent_month` carries the rent metrics.",
        "",
        *md_table(["rpt view", "Values checked", "Mismatches"], checks),
        "",
    ]
    if result.mismatches:
        lines += [
            *md_table(
                ["rpt view", "Period", "Metric", "Silver", "rpt", "Tolerance"],
                [
                    (m.source, m.period, m.metric, m.silver, m.other, m.tolerance)
                    for m in result.mismatches[:50]
                ],
            ),
            "",
        ]
    lines += [
        "## 5. Sanity check: residential apartments, area-weighted vs median AED per sq m",
        "",
        f"Must be within ±{DIVERGENCE_TOLERANCE:.0%} of each other in every year from "
        f"{DIVERGENCE_FROM_YEAR}. A wider gap would mean plot- or building-sized areas are "
        "still leaking into the area-weighted sums (or a unit mix shift worth explaining).",
        "",
        *(
            []
            if applies
            else [
                f"**Not applicable here**: fewer than {DIVERGENCE_MIN_LINES:,} transaction "
                "lines in scope (fixture or sample data), so yearly apartment figures are noise.",
                "",
            ]
        ),
        *md_table(
            [
                "Year",
                "Median AED / sq m",
                "Area-weighted AED / sq m",
                "Area-weighted / median %",
                "Check",
            ],
            apt_rows,
        ),
        "",
        "## 6. KPIs pending the models",
        "",
        *md_table(["KPI", "Source"], PENDING),
        "",
    ]
    return "\n".join(lines)


def run(path: Path = REPORT_PATH) -> Result:
    """Compute, compare and write the report."""
    t0 = time.perf_counter()
    with db.connect() as conn:
        if not rpt_available(conn):
            raise RuntimeError("rpt views not built: run `make dbt` first")
        result = compute(conn)
    path.write_text(render(result))
    log.info(
        "kpi reconciliation written to %s in %.0fs: %d mismatch(es), %d apartment divergence(s)",
        path,
        time.perf_counter() - t0,
        len(result.mismatches),
        len(divergence_failures(result.silver)),
    )
    return result


def main() -> int:
    """CLI entry point. Exits 1 if any KPI doesn't reconcile or the sanity check fails."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run()
    return 1 if result.mismatches or divergence_failures(result.silver) else 0


if __name__ == "__main__":
    sys.exit(main())
