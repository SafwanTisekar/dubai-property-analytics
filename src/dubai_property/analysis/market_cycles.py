"""Q1: how have transaction volume and value moved through each market cycle since 2004?

Market sales follow docs/01 §4: ``is_market_sale`` lines, AED counted once per deal (C16).
Volumes come from ``gold.agg_area_month`` (additive, reconciled to the fact in Phase 2b).
The 2009 investigation reads ``gold.fct_transaction`` but only returns grouped counts.

**Registration timing.** DLD's ``transaction_id`` is ``<group>-<procedure>-<year>-<seq>``.
Phase 1 (phase1_findings §4) found the ID year behaves like the *application* year, which
normally equals the registration year. Where it runs years ahead of ``txn_date``, the
line was registered long after the deal was struck: a backlog, not new activity.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sqlalchemy import Engine

from dubai_property import config
from dubai_property.analysis.common import query


@dataclass(frozen=True)
class Phase:
    """A market phase shaded on the time-series charts."""

    label: str
    start_year: int
    end_year: int | None  # None = still running at the snapshot
    note: str


# The cycles named in docs/01 §1. Year boundaries are deliberately coarse: they label
# context on a chart, they are not a dating of turning points (the Phase 4 index does that).
CYCLE_PHASES: tuple[Phase, ...] = (
    Phase("2008–09 crash", 2008, 2009, "Global financial crisis; Dubai World debt standstill"),
    Phase("2014–19 correction", 2014, 2019, "Oil-price fall, strong USD (AED peg), oversupply"),
    Phase("2020 COVID", 2020, 2020, "Lockdowns; the cycle low in volumes"),
    Phase("2021+ boom", 2021, None, "Record volumes led by off-plan sales"),
)

_SCOPE = "month between :start and :end"

SALES_BY_MONTH_SQL = f"""
select month,
       sum(market_sales) as market_sales,
       sum(market_sales) filter (where is_offplan) as offplan_sales,
       sum(market_sales_value_aed) as market_value_aed,
       sum(market_sales_value_aed) filter (where is_offplan) as offplan_value_aed,
       sum(new_mortgages) as new_mortgages
from gold.agg_area_month
where {_SCOPE}
group by month
order by month
"""

SALES_BY_PROCEDURE_SQL = """
select extract(year from txn_date)::int as year, procedure_name, is_offplan,
       count(*) as market_sales, sum(aed_counted_once) as market_value_aed
from gold.fct_transaction
where is_market_sale and is_in_report_scope
  and extract(year from txn_date) between :first_year and :last_year
group by 1, 2, 3
order by 1, 2, 3
"""

# id_year = the year segment of transaction_id. Only market sales, only in scope.
REGISTRATION_LAG_SQL = """
select extract(year from txn_date)::int as year, is_offplan,
       split_part(transaction_id, '-', 3)::int as id_year,
       count(*) as market_sales
from gold.fct_transaction
where is_market_sale and is_in_report_scope
  and extract(year from txn_date) between :first_year and :last_year
group by 1, 2, 3
order by 1, 2, 3
"""

# First year a project appears in the register (any procedure). Circular as evidence of
# launch dates (it comes from the same register), so it is shown as a table, not a proof.
OFFPLAN_BY_PROJECT_FIRST_YEAR_SQL = """
select extract(year from p.first_txn_date)::int as project_first_year,
       count(*) as offplan_sales, count(distinct t.project_key) as projects
from gold.fct_transaction as t
join gold.dim_project as p using (project_key)
where t.is_market_sale and t.is_offplan and extract(year from t.txn_date) = :year
group by 1
order by 1
"""

# Clean sales of residential apartments: median AED per sq m, off-plan vs ready.
PPSQM_OFFPLAN_VS_READY_SQL = """
select extract(year from txn_date)::int as year, is_offplan,
       count(*) as clean_sales,
       percentile_cont(0.5) within group (order by price_per_sqm_aed) as median_ppsqm_aed
from gold.fct_transaction
where is_clean_market_sale and is_in_report_scope and property_type_key = :ptk
  and extract(year from txn_date) between :first_year and :last_year
group by 1, 2
order by 1, 2
"""


def sales_by_month(start, end, engine: Engine | None = None) -> pd.DataFrame:
    """Market sales count and AED by month, total and off-plan, plus new mortgages.

    Args:
        start: First day in scope (``config.REPORT_SCOPE_START``).
        end: Last day in scope (the snapshot date).
        engine: Optional SQLAlchemy engine.
    """
    df = query(SALES_BY_MONTH_SQL, {"start": start, "end": end}, engine)
    df["month"] = pd.to_datetime(df["month"])
    for col in df.columns.drop("month"):
        df[col] = df[col].fillna(0).astype("float64")
    df["ready_sales"] = df["market_sales"] - df["offplan_sales"]
    df["ready_value_aed"] = df["market_value_aed"] - df["offplan_value_aed"]
    return df


def sales_by_year(start, end, engine: Engine | None = None) -> pd.DataFrame:
    """Market sales by calendar year (same columns as ``sales_by_month``) plus shares."""
    monthly = sales_by_month(start, end, engine)
    df = monthly.groupby(monthly["month"].dt.year).sum(numeric_only=True)
    df.index.name = "year"
    df = df.reset_index()
    df["offplan_share_count"] = df["offplan_sales"] / df["market_sales"]
    df["offplan_share_value"] = df["offplan_value_aed"] / df["market_value_aed"]
    df["yoy_sales"] = df["market_sales"].pct_change()
    return df


def sales_by_procedure(
    first_year: int, last_year: int, engine: Engine | None = None
) -> pd.DataFrame:
    """Market sales by year × procedure × off-plan (the 2009 spike split)."""
    params = {"first_year": first_year, "last_year": last_year}
    return query(SALES_BY_PROCEDURE_SQL, params, engine)


def registration_lag(first_year: int, last_year: int, engine: Engine | None = None):
    """Market sales by registration year × off-plan × transaction_id year.

    Adds ``lag_years`` = registration year − id year. A backlog shows up as off-plan
    registrations carrying ID years well before the year they were registered.
    """
    params = {"first_year": first_year, "last_year": last_year}
    df = query(REGISTRATION_LAG_SQL, params, engine)
    df["lag_years"] = df["year"] - df["id_year"]
    return df


def registration_lag_summary(lag: pd.DataFrame) -> pd.DataFrame:
    """Per year × off-plan: lines, share with an earlier ID year, median lag in years."""

    def _one(g: pd.DataFrame) -> pd.Series:
        n = g["market_sales"].sum()
        earlier = g.loc[g["lag_years"] > 0, "market_sales"].sum()
        # Weighted median of the lag (each row is a count of lines).
        ordered = g.sort_values("lag_years")
        cum = ordered["market_sales"].cumsum()
        median = ordered.loc[cum >= n / 2, "lag_years"].iloc[0] if n else float("nan")
        return pd.Series(
            {"market_sales": n, "share_id_year_earlier": earlier / n, "median_lag_years": median}
        )

    return (
        lag.groupby(["year", "is_offplan"])[["market_sales", "lag_years"]].apply(_one).reset_index()
    )


def offplan_by_project_first_year(year: int, engine: Engine | None = None) -> pd.DataFrame:
    """Off-plan market sales registered in ``year`` by the project's first register year."""
    return query(OFFPLAN_BY_PROJECT_FIRST_YEAR_SQL, {"year": year}, engine)


def ppsqm_offplan_vs_ready(
    first_year: int,
    last_year: int,
    property_type_key: int = config.RESIDENTIAL_APARTMENT_KEY,
    engine: Engine | None = None,
) -> pd.DataFrame:
    """Median AED per sq m of clean sales, off-plan vs ready, by year (one property type)."""
    params = {"first_year": first_year, "last_year": last_year, "ptk": property_type_key}
    return query(PPSQM_OFFPLAN_VS_READY_SQL, params, engine)


# --- Momentum: year to date vs the same months a year earlier ----------------------------
# Only whole months: the snapshot month is partial, so "YTD" runs to the last full month.
YTD_BY_ZONE_SQL = """
select a.zone, extract(year from t.txn_date)::int as year, t.is_offplan,
       count(*) as market_sales, sum(t.aed_counted_once) as market_value_aed
from gold.fct_transaction as t
join gold.dim_area as a using (area_key)
where t.is_market_sale and t.is_in_report_scope
  and extract(year from t.txn_date) in (:year, :year - 1)
  and extract(month from t.txn_date) between 1 and :last_month
group by 1, 2, 3
"""

# Every registration (all groups) per day: a registration lag at the snapshot would show
# as a tail of thin days just before it.
DAILY_REGISTRATIONS_SQL = """
select txn_date, extract(isodow from txn_date)::int as iso_dow,
       count(*) as transaction_lines, count(*) filter (where is_market_sale) as market_sales
from gold.fct_transaction
where txn_date between :start and :end
group by 1, 2
order by 1
"""


def last_full_month(snapshot) -> int:
    """The last complete month of the snapshot year (the snapshot month is partial)."""
    ts = pd.Timestamp(snapshot)
    return ts.month if ts.is_month_end else ts.month - 1


def ytd_by_zone(snapshot, engine: Engine | None = None) -> pd.DataFrame:
    """Market sales by zone × off-plan, Jan → last full month, snapshot year vs a year earlier.

    Returns one row per zone × off-plan flag with ``sales_prev``, ``sales_cur``,
    ``value_prev_aed``, ``value_cur_aed``.
    """
    year = pd.Timestamp(snapshot).year
    params = {"year": year, "last_month": last_full_month(snapshot)}
    df = query(YTD_BY_ZONE_SQL, params, engine)
    df["market_value_aed"] = df["market_value_aed"].astype("float64")
    wide = df.pivot_table(
        index=["zone", "is_offplan"],
        columns="year",
        values=["market_sales", "market_value_aed"],
        aggfunc="sum",
        fill_value=0,
    )
    wide.columns = [
        f"{'sales' if m == 'market_sales' else 'value'}_{'cur' if y == year else 'prev'}"
        + ("_aed" if m == "market_value_aed" else "")
        for m, y in wide.columns
    ]
    return wide.reset_index()


def ytd_summary(by_zone: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """Sum ``ytd_by_zone`` to any grouping (default: all) and add % changes."""
    cols = ["sales_prev", "sales_cur", "value_prev_aed", "value_cur_aed"]
    g = by_zone.groupby(by)[cols].sum().reset_index() if by else by_zone[cols].sum().to_frame().T
    g["sales_change"] = g["sales_cur"] / g["sales_prev"] - 1
    g["value_change"] = g["value_cur_aed"] / g["value_prev_aed"] - 1
    return g


def daily_registrations(start, end, engine: Engine | None = None) -> pd.DataFrame:
    """Transaction lines and market sales per registration day (all groups)."""
    df = query(DAILY_REGISTRATIONS_SQL, {"start": start, "end": end}, engine)
    df["txn_date"] = pd.to_datetime(df["txn_date"])
    return df


def snapshot_tail_ratio(daily: pd.DataFrame, snapshot, tail_days: int = 7) -> float:
    """Lines per working day in the last ``tail_days`` days vs the 4 weeks before them.

    A registration lag at the extract would make recent days thin (ratio well below 1).
    Weekends (Sat, Sun) are dropped; Friday is a short day in Dubai but appears in both
    windows.
    """
    d = daily[daily["iso_dow"] <= 5].set_index("txn_date")["transaction_lines"]
    end = pd.Timestamp(snapshot)
    tail = d[d.index > end - pd.Timedelta(days=tail_days)]
    base = d[
        (d.index <= end - pd.Timedelta(days=tail_days))
        & (d.index > end - pd.Timedelta(days=tail_days + 28))
    ]
    return float(tail.mean() / base.mean())
