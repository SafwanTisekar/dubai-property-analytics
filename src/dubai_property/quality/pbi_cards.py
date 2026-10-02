"""Power BI card checklist: the value every KPI card must show, with the filters to set.

Rendered as §7 of ``reports/kpi_reconciliation.md`` (``make kpi``). ``powerbi/BUILD.md``
links to it rather than copying numbers, so a refresh never leaves a stale target behind.

* **Pre-ML cards** take their values from the canonical silver figures that §1–3 of the
  report already reconcile against ``rpt.transactions`` / ``area_month`` / ``rent_month``.
* **Post-ML cards** (index, yields, AVM, stress, forecast, master-project proxy) are
  computed here from the rpt views, with the same population and logic as the DAX measure
  named in the card (``powerbi/.../tables/_Measures.tmdl``). They appear only once
  ``make score`` has built the post_ml views, so the pre-ML CI build stays valid.

Every query reads small rpt views or aggregates in SQL; nothing large leaves Postgres.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import psycopg

from dubai_property import config
from dubai_property.quality.dq_report import md_table

# The year the report opens on (BUILD.md: the Year slicer defaults to the latest complete
# year). The snapshot year is partial, so it is never the default.
DEFAULT_SHOCK = -20
DEFAULT_LTV = 80
DEFAULT_SCENARIO = "Rates flat"
REVIEW_FLAG = "Review: statistical anomaly"
POST_ML_VIEWS = (
    "price_index",
    "yield_quarter",
    "avm_performance",
    "avm_score",
    "stress_grid",
    "forecast",
)


@dataclass(frozen=True)
class Card:
    """One card to check in Power BI Desktop."""

    page: str
    card: str  # the measure in _Measures.tmdl
    filters: str  # slicer state to set before reading the card
    expected: str  # formatted as the card displays it
    source: str  # where the expected value comes from


# --- Formatting (as the measures' format strings display them) --------------------------


def _half_up(x: Any, digits: int) -> Decimal:
    """Round like Power BI's format strings: half away from zero, on the exact decimal."""
    return Decimal(str(x)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)


def pct(x: Any, digits: int = 1) -> str:
    """0.2794 -> '27.9%' (blank stays blank); 0.6505 -> '65.1%', as Power BI shows it."""
    return "(blank)" if x is None else f"{_half_up(Decimal(str(x)) * 100, digits)}%"


def signed_pct(x: Any) -> str:
    """0.046 -> '+4.6%'."""
    if x is None:
        return "(blank)"
    v = _half_up(Decimal(str(x)) * 100, 1)
    return f"{'+' if v >= 0 else ''}{v}%"


def aed_bn(x: Any) -> str:
    """668_312_000_000 -> 'AED 668.3bn'."""
    return "(blank)" if x is None else f"AED {float(x) / 1e9:,.1f}bn"


def aed(x: Any) -> str:
    """17828.4 -> 'AED 17,828'."""
    return "(blank)" if x is None else f"AED {round(float(x)):,}"


def num(x: Any, digits: int = 0) -> str:
    """Thousands separators; ``digits`` decimals."""
    return "(blank)" if x is None else f"{float(x):,.{digits}f}"


# --- Pre-ML cards from the silver table of the KPI report ------------------------------


def latest_complete_year(silver: dict[str, dict[str, Any]], snapshot_year: int) -> str:
    """The latest full calendar year in the data (the report's default Year)."""
    years = sorted(int(p) for p in silver if len(p) == 4 and int(p) < snapshot_year)
    return str(years[-1] if years else snapshot_year)


def pre_ml_cards(
    silver: dict[str, dict[str, Any]],
    derive: Callable[[dict[str, Any]], dict[str, float | None]],
    year: str,
) -> list[Card]:
    """Executive, Financing and Yields cards that come from the reconciled silver KPIs."""
    out: list[Card] = []
    for period, filters in ((year, f"Year = {year}"), ("all", "no Year selected")):
        r = silver.get(period, {})
        d = derive(r)
        src = "kpi_reconciliation §1–2 (silver = rpt)"
        p1, p2 = "1 Executive", "2 Financing"
        out += [
            Card("1 Executive", "Market Sales Value", filters, aed_bn(r.get("market_value")), src),
            Card("1 Executive", "Market Sales", filters, num(r.get("market_sales")), src),
            Card("1 Executive", "Median Price per Sq M", filters, aed(r.get("median_ppsqm")), src),
            Card(
                "1 Executive",
                "Purchase Mortgage Share",
                filters,
                pct(d["purchase_mortgage_share"]),
                src,
            ),
            Card(p1, "Off-Plan Share (Value)", filters, pct(d["offplan_share_value"]), src),
        ]
        if period != year:
            continue
        out += [
            Card("2 Financing", "Ready Market Sales", filters, num(r.get("ready_sales")), src),
            Card(p2, "Purchase Mortgages", filters, num(r.get("purchase_mortgages")), src),
            Card(
                "2 Financing",
                "New Mortgages per 100 Sales",
                filters,
                num(d["new_mortgages_per_100"], 1),
                src,
            ),
            Card(p2, "Off-Plan Share (Count)", filters, pct(d["offplan_share_count"]), src),
            Card(p2, "Portfolio Mortgage Deals", filters, num(r.get("portfolio_deals")), src),
            Card(
                "3 Prices",
                "Area-Weighted Price per Sq M (Homes)",
                filters,
                aed(d["aw_ppsqm"]),
                src,
            ),
            Card("4 Yields", "New Market Rents", filters, num(r.get("market_rents")), src),
            Card(
                "4 Yields",
                "Area-Weighted New Rent per Sq M (Homes)",
                filters,
                aed(d["rent_aw_sqm"]),
                src,
            ),
        ]
    return out


# --- Post-ML cards from the rpt views --------------------------------------------------


def post_ml_available(conn: psycopg.Connection) -> bool:
    """True once ``make score`` has built every post_ml view the cards read."""
    (n,) = conn.execute(
        "select count(*) from pg_views where schemaname = 'rpt' and viewname = any(%s)",
        [list(POST_ML_VIEWS)],
    ).fetchone()
    return n == len(POST_ML_VIEWS)


def _one(conn: psycopg.Connection, sql: str, params: dict | None = None) -> tuple:
    """First row, or NULLs of the same width when there is none (e.g. CI fixtures)."""
    cur = conn.execute(sql, params or {})
    row = cur.fetchone()
    return row if row is not None else (None,) * len(cur.description)


# [Index YoY] and [Index Value]: the segment's latest complete (non-partial) monthly period
# on or before the end of the selected year.
INDEX_SQL = """
select "Period Start", "Index Value", "YoY Change", "Drawdown"
from rpt.price_index
where "Segment" = %(segment)s and not "Is Partial Period"
    and "Period Start" <= %(until)s
order by "Period Start" desc
limit 1
"""
MAX_DRAWDOWN_SQL = """
select min("Drawdown") from rpt.price_index where "Segment" = %(segment)s
"""
# [Gross Yield]: sales-weighted mean over zone cells of the last four complete quarters,
# cells outside the 2-15% sanity band left out (reports/yields.md headline, Phase 5).
YIELD_SQL = """
with zone as (
    select * from rpt.yield_quarter
    where "Geo Level" = 'Zone' and not "Is Partial Period" and not "Is Outside Sanity Band"
),
last_q as (select max("Quarter Start") as q from zone)
select sum("Gross Yield" * "Sales") / sum("Sales"),
       min("Quarter Start"), max("Quarter Start")
from zone, last_q
where "Property Type Key" = %(ptype)s and "Quarter Start" > q - interval '1 year'
"""
AVM_PERF_SQL = """
select "MdAPE", "Hit Rate 10 Pct", "Hit Rate 20 Pct"
from rpt.avm_performance
where "Model" = %(model)s and "Split" = 'Test' and "Breakdown" = 'Overall'
"""
AVM_SCORE_SQL = f"""
select count(*),
       percentile_cont(0.5) within group (order by "Absolute Error Pct"),
       avg(("Review Flag" = '{REVIEW_FLAG}')::int)
from rpt.avm_score where "Model Set" = 'Test'
"""
# [Negative Equity Share] / [Negative Equity AED]: one segment, Ready, the selected shock
# and LTV on the assumed-LTV grid.
STRESS_SQL = """
select "Negative Equity Share", "Negative Equity AED"
from rpt.stress_grid
where "Segment" = %(segment)s and "Ready / Off-Plan" = 'Ready' and "Scenario" = %(scenario)s
    and "Loan Basis" = %(basis)s
    and ("Shock Pct" = %(shock)s or (%(shock)s is null and "Shock Pct" is null))
    and ("LTV Pct" = %(ltv)s or (%(ltv)s is null and "LTV Pct" is null))
"""
# [Forecast 12M Change]: the scenario's last forecast month vs the last actual month.
FORECAST_SQL = """
with f as (select * from rpt.forecast where "Target" = 'Price index' and "Segment" = %(segment)s),
last_actual as (
    select "Actual" from f where "Scenario" = 'Actual' order by "Month" desc limit 1
),
last_fc as (
    select "Forecast", "Lower 80", "Upper 80" from f
    where "Scenario" = %(scenario)s order by "Month" desc limit 1
)
select fc."Forecast" / a."Actual" - 1,
       fc."Lower 80" / a."Actual" - 1,
       fc."Upper 80" / a."Actual" - 1
from last_actual a, last_fc fc
"""
# [Top 10 Master Project Share] / [Master Project HHI]: off-plan market sales of the year by
# master project (known master projects only), a proxy for developer concentration.
MASTER_PROJECT_SQL = """
with s as (
    select p."Master Project" as mp, count(*) as n
    from rpt.transactions t
    join rpt.dim_project p using ("Project Key")
    where t."Is Market Sale" and t."Is Off-Plan"
        and t."Date" >= make_date(%(year)s, 1, 1) and t."Date" < make_date(%(year)s + 1, 1, 1)
        and p."Master Project" is not null and p."Master Project" <> 'Unknown'
    group by 1
),
r as (select n, row_number() over (order by n desc) as rk, sum(n) over () as tot from s)
select sum(n) filter (where rk <= 10)::numeric / max(tot),
       sum(power(n::numeric / tot, 2)) * 10000
from r
"""


def post_ml_cards(conn: psycopg.Connection, year: str) -> list[Card]:
    """Cards for the model pages, computed from the rpt views."""
    out: list[Card] = []
    y_end = f"{year}-12-31"
    src_index = "rpt.price_index (latest complete month)"
    for segment, page in (
        ("Dubai (all residential)", "1 Executive"),
        ("Apartments", "3 Prices"),
        ("Villas / Townhouses", "3 Prices"),
    ):
        for until, filt in ((y_end, f"Year = {year}"), ("9999-12-31", "no Year selected")):
            if page == "3 Prices" and until == y_end:
                continue
            period, value, yoy, dd = _one(conn, INDEX_SQL, {"segment": segment, "until": until})
            filters = f"{filt}; index segment = {segment} ({period:%b %Y})" if period else filt
            out.append(Card(page, "Index YoY", filters, signed_pct(yoy), src_index))
            if page == "3 Prices":
                out.append(
                    Card(page, "Index Value (Latest Complete)", filters, num(value, 1), src_index)
                )
                out.append(Card(page, "Drawdown from Peak", filters, pct(dd), src_index))
        if page == "3 Prices" or segment.startswith("Dubai"):
            (mdd,) = _one(conn, MAX_DRAWDOWN_SQL, {"segment": segment})
            out.append(
                Card(
                    "3 Prices",
                    "Max Drawdown",
                    f"no Year selected; index segment = {segment}",
                    pct(mdd),
                    src_index,
                )
            )

    for ptype, label in (
        (config.RESIDENTIAL_APARTMENT_KEY, "Residential · Apartment"),
        (102, "Residential · Villa / Townhouse"),
    ):
        y, q0, q1 = _one(conn, YIELD_SQL, {"ptype": ptype})
        quarters = f"{q0:%Y-%m} to {q1:%Y-%m} quarter starts" if q0 else "no quarters"
        out.append(
            Card(
                "4 Yields",
                "Gross Yield (Latest 4 Quarters)",
                f"Property Type = {label}; {quarters}",
                pct(y),
                "rpt.yield_quarter, zone cells, sales-weighted (yields.md)",
            )
        )

    for model, label in (("lightgbm", "LightGBM"), ("comps", "Comparable sales (baseline)")):
        mdape, h10, h20 = _one(conn, AVM_PERF_SQL, {"model": model})
        suffix = "" if model == "lightgbm" else " (Baseline)"
        src = f"rpt.avm_performance, {label}, Test / Overall"
        out += [
            Card("5 Valuation", f"AVM Test MdAPE{suffix}", "none", pct(mdape, 2), src),
            Card("5 Valuation", f"AVM Test Hit Rate 10%{suffix}", "none", pct(h10), src),
            Card("5 Valuation", f"AVM Test Hit Rate 20%{suffix}", "none", pct(h20), src),
        ]
    n, mdape, flagged = _one(conn, AVM_SCORE_SQL)
    src = "rpt.avm_score, Model Set = Test"
    filt = "Model Set = Test (page filter); other slicers clear"
    out += [
        Card("5 Valuation", "Valued Sales", filt, num(n), src),
        Card("5 Valuation", "AVM MdAPE (Interactive)", filt, pct(mdape, 2), src),
        Card("5 Valuation", "Flagged Share", filt, pct(flagged), src),
    ]

    grid = {"scenario": "Price shock", "basis": "Assumed LTV"}
    for segment in ("Dubai (all residential)", "Apartments", "Villas / Townhouses"):
        for shock in (-10, DEFAULT_SHOCK, -30):
            share, ne_aed = _one(
                conn, STRESS_SQL, {**grid, "segment": segment, "shock": shock, "ltv": DEFAULT_LTV}
            )
            filters = f"Stress segment = {segment}; Ready; Shock {shock}; LTV {DEFAULT_LTV}"
            src = "rpt.stress_grid"
            out.append(Card("6 Risk", "Negative Equity Share", filters, pct(share), src))
            if shock == DEFAULT_SHOCK and segment.startswith("Dubai"):
                out.append(Card("6 Risk", "Negative Equity AED", filters, aed_bn(ne_aed), src))
        for scenario, depth in (
            ("Replay: 2014-2020, Dubai-wide", "Dubai-wide (lower range)"),
            ("Replay: 2014-2020, own series", "Own series (upper range)"),
        ):
            (share, _) = _one(
                conn,
                STRESS_SQL,
                {"scenario": scenario, "basis": "Assumed LTV", "segment": segment,
                 "shock": None, "ltv": DEFAULT_LTV},
            )  # fmt: skip
            out.append(
                Card(
                    "6 Risk",
                    "Replay Negative Equity Share",
                    f"Stress segment = {segment}; Ready; LTV {DEFAULT_LTV}; Replay Depth = {depth}",
                    pct(share),
                    "rpt.stress_grid",
                )
            )
    # Dubai-wide the two references nearly coincide (20.69% vs 20.73%, both "20.7%"): the
    # two decimals show they are different rows; apartments separate them clearly.
    for segment in ("Dubai (all residential)", "Apartments"):
        for basis, card in (
            ("CBUAE cap (expatriate, first home)", "Negative Equity Share (CBUAE Cap)"),
            ("Registered loan (matched purchases)", "Negative Equity Share (Registered Loans)"),
        ):
            (share, _) = _one(
                conn,
                STRESS_SQL,
                {"scenario": "Price shock", "basis": basis, "segment": segment,
                 "shock": DEFAULT_SHOCK, "ltv": None},
            )  # fmt: skip
            out.append(
                Card(
                    "6 Risk",
                    card,
                    f"Stress segment = {segment}; Ready; Shock {DEFAULT_SHOCK}",
                    f"{pct(share)} ({pct(share, 2)})",
                    "rpt.stress_grid",
                )
            )

    for segment in ("Dubai (all residential)", "Apartments", "Villas / Townhouses"):
        central, lo, hi = _one(
            conn, FORECAST_SQL, {"segment": segment, "scenario": DEFAULT_SCENARIO}
        )
        filters = f"Forecast segment = {segment}; Scenario = {DEFAULT_SCENARIO}"
        out += [
            Card("6 Risk", "Forecast 12M Change", filters, signed_pct(central), "rpt.forecast"),
            Card(
                "6 Risk",
                "Forecast 12M Band 80% Label",
                filters,
                f"{signed_pct(lo)} to {signed_pct(hi)}",
                "rpt.forecast (forecast.md)",
            ),
        ]

    top10, hhi = _one(conn, MASTER_PROJECT_SQL, {"year": int(year)})
    src = "rpt.transactions + rpt.dim_project (proxy, not developer HHI)"
    out += [
        Card("6 Risk", "Top 10 Master Project Share (Off-Plan)", f"Year = {year}", pct(top10), src),
        Card("6 Risk", "Master Project HHI (Off-Plan)", f"Year = {year}", num(hhi), src),
    ]
    return out


COLUMNS = ["Page", "Card (measure)", "Filters to set", "Expected", "Source"]


def rows(cards: list[Card]) -> list[tuple[str, str, str, str, str]]:
    """Table rows for the report."""
    return [(c.page, c.card, c.filters, c.expected, c.source) for c in cards]


def render(pre: list[Card], post: list[Card] | None, year: str) -> list[str]:
    """§7 of the KPI report."""
    lines = [
        "## 7. Power BI card checklist",
        "",
        "Set the filters, read the card, tick it. Every other slicer is cleared unless "
        f"listed. The report opens on **Year = {year}** (the latest complete year; the "
        "snapshot year is partial). Values are as the measures' format strings display "
        "them; a last-digit difference is rounding, anything more is a bug. AED amounts "
        'are formatted "AED "#,0 in the model, so bn values assume the card\'s display '
        "units = Billions with 1 decimal (Auto would switch to Trillions on all-time "
        "totals). Measure "
        "definitions: `powerbi/DubaiProperty.SemanticModel/definition/tables/_Measures.tmdl`.",
        "",
        *md_table(COLUMNS, rows(pre)),
        "",
    ]
    if post is None:
        lines += [
            "Model cards (index, yields, AVM, stress, forecast) appear here once `make score` "
            f"has built the post_ml views, then `make kpi`. Expected defaults: shock "
            f"{DEFAULT_SHOCK}%, LTV {DEFAULT_LTV}%, scenario {DEFAULT_SCENARIO}.",
            "",
        ]
    else:
        lines += [
            f"Model cards. Defaults: shock {DEFAULT_SHOCK}%, LTV {DEFAULT_LTV}%, Ready, "
            f"scenario {DEFAULT_SCENARIO}, AVM page filtered to the test period. "
            f"Min-n is {config.MIN_N}: a blank card means the segment is below it.",
            "",
            *md_table(COLUMNS, rows(post)),
            "",
        ]
    return lines
