"""Q3 (price per sq m by area, type and bedrooms) and a Q4 preview (gross yields).

Populations (docs/01 §4, docs/04):

* **Prices**: clean market sales (``is_clean_market_sale``). The median AED per sq m is
  exact (``percentile_cont`` over sales). The area-weighted figure is Σ AED ÷ Σ sq m from
  ``gold.agg_area_month``, over sales within the class area cap, per property class.
* **Rents**: new market rents (``is_market_rent``: new, single-line, comparable). Rent per
  sq m only where the line has a real area (C21).
* **Min-n** (CLAUDE.md): a segment with fewer than 20 observations gets no median; the
  functions return n and blank the value, and the yield preview rolls up to the zone.

Everything is grouped in SQL. ``fct_rent_contract`` (10.5M lines) never leaves Postgres.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import Engine

from dubai_property import config
from dubai_property.analysis.common import apply_min_n, query

HOMES = list(config.RESIDENTIAL_HOMES_KEYS)
YIELD_SANITY = config.YIELD_SANITY  # docs/04 §4; shared with models/yields.py

PPSQM_BY_YEAR_SQL = """
with med as (
    select extract(year from txn_date)::int as year, property_type_key,
           count(*) as clean_sales,
           percentile_cont(0.5) within group (order by price_per_sqm_aed) as median_ppsqm_aed
    from gold.fct_transaction
    where is_clean_market_sale and is_in_report_scope and property_type_key = any(:keys)
    group by 1, 2
),
aw as (
    select extract(year from month)::int as year, property_type_key,
           sum(clean_sales_value_aed) / nullif(sum(clean_sales_area_sqm), 0) as aw_ppsqm_aed
    from gold.agg_area_month
    where property_type_key = any(:keys)
    group by 1, 2
)
select med.year, med.property_type_key, pt.property_type_label, med.clean_sales,
       med.median_ppsqm_aed, aw.aw_ppsqm_aed
from med
join aw using (year, property_type_key)
join gold.dim_property_type as pt using (property_type_key)
order by 2, 1
"""

PPSQM_BY_ZONE_YEAR_SQL = """
select a.zone, extract(year from t.txn_date)::int as year, count(*) as clean_sales,
       percentile_cont(0.5) within group (order by t.price_per_sqm_aed) as median_ppsqm_aed
from gold.fct_transaction as t
join gold.dim_area as a using (area_key)
where t.is_clean_market_sale and t.is_in_report_scope and t.property_type_key = any(:keys)
group by 1, 2
order by 1, 2
"""

RENT_PPSQM_BY_ZONE_YEAR_SQL = """
select a.zone, extract(year from r.start_date)::int as year, count(*) as rent_n,
       percentile_cont(0.5) within group (order by r.rent_per_sqm_aed) as median_rent_ppsqm_aed
from gold.fct_rent_contract as r
join gold.dim_area as a using (area_key)
where r.is_market_rent and r.is_in_report_scope and r.rent_per_sqm_aed is not null
  and r.property_type_key = any(:keys)
group by grouping sets ((a.zone, extract(year from r.start_date)),
                        (extract(year from r.start_date)))
order by 1 nulls first, 2
"""

TOP_AREAS_SQL = """
with cur as (
    select area_key, sum(market_sales) as market_sales,
           sum(market_sales_value_aed) as market_value_aed,
           sum(market_sales_value_aed) filter (where is_offplan) as offplan_value_aed
    from gold.agg_area_month
    where month between :start and :end
    group by 1
),
prev as (
    select area_key, sum(market_sales_value_aed) as prior_value_aed
    from gold.agg_area_month
    where month between :prev_start and :prev_end
    group by 1
)
select a.area_name, a.zone, cur.market_sales, cur.market_value_aed,
       coalesce(cur.offplan_value_aed, 0) / nullif(cur.market_value_aed, 0) as offplan_share_value,
       prev.prior_value_aed,
       cur.market_value_aed / sum(cur.market_value_aed) over () as share_of_dubai_value
from cur
join gold.dim_area as a using (area_key)
left join prev using (area_key)
order by cur.market_value_aed desc
"""

# Mix shift: cells = zone × bedrooms within one property class (the class is fixed by the
# key), and the raw yearly median with the off-plan share of the same population.
MIX_CELLS_SQL = """
select extract(year from t.txn_date)::int as year, a.zone,
       coalesce(t.bedrooms, -1) as bedrooms, count(*) as n,
       percentile_cont(0.5) within group (order by t.price_per_sqm_aed) as median_ppsqm_aed
from gold.fct_transaction as t
join gold.dim_area as a using (area_key)
where t.is_clean_market_sale and t.is_in_report_scope and t.property_type_key = :ptk
group by 1, 2, 3
"""

MIX_RAW_SQL = """
select extract(year from txn_date)::int as year, count(*) as n,
       percentile_cont(0.5) within group (order by price_per_sqm_aed) as median_ppsqm_aed,
       avg(is_offplan::int) as offplan_share
from gold.fct_transaction
where is_clean_market_sale and is_in_report_scope and property_type_key = :ptk
group by 1
order by 1
"""

# Yield preview: last 12 months, ready clean sales vs new market rents, both at
# zone × property class × bedrooms (cells) and zone × property class (roll-up).
YIELD_PREVIEW_SQL = """
with sales as (
    select a.zone, t.property_type_key, t.bedrooms, grouping(t.bedrooms) as is_rollup,
           count(*) as sales_n,
           percentile_cont(0.5) within group (order by t.actual_worth_aed) as median_price_aed
    from gold.fct_transaction as t
    join gold.dim_area as a using (area_key)
    where t.is_clean_market_sale and not t.is_offplan and t.property_type_key = any(:keys)
      and t.txn_date between :start and :end
    group by grouping sets ((a.zone, t.property_type_key, t.bedrooms),
                            (a.zone, t.property_type_key))
),
rents as (
    select a.zone, r.property_type_key, r.bedrooms, grouping(r.bedrooms) as is_rollup,
           count(*) as rent_n,
           percentile_cont(0.5) within group (order by r.annual_rent_alloc_aed)
               as median_annual_rent_aed
    from gold.fct_rent_contract as r
    join gold.dim_area as a using (area_key)
    where r.is_market_rent and r.property_type_key = any(:keys)
      and r.start_date between :start and :end
    group by grouping sets ((a.zone, r.property_type_key, r.bedrooms),
                            (a.zone, r.property_type_key))
)
select s.zone, s.property_type_key, pt.property_type_label, s.bedrooms,
       s.is_rollup = 1 as is_rollup, s.sales_n, s.median_price_aed,
       r.rent_n, r.median_annual_rent_aed
from sales as s
join rents as r
    on r.zone = s.zone and r.property_type_key = s.property_type_key
    and r.is_rollup = s.is_rollup
    and r.bedrooms is not distinct from s.bedrooms
join gold.dim_property_type as pt on pt.property_type_key = s.property_type_key
where not (s.is_rollup = 0 and s.bedrooms is null)  -- unknown bedrooms only in the roll-up
order by 1, 2, 4
"""


def ppsqm_by_year(keys: list[int] = HOMES, engine: Engine | None = None) -> pd.DataFrame:
    """Median and area-weighted AED per sq m by year for each property type key."""
    df = query(PPSQM_BY_YEAR_SQL, {"keys": list(keys)}, engine)
    return df.astype({"median_ppsqm_aed": "float64", "aw_ppsqm_aed": "float64"})


def ppsqm_by_zone_year(keys: list[int] = HOMES, engine: Engine | None = None) -> pd.DataFrame:
    """Median AED per sq m by zone × year (min-n applied), for the given property types."""
    df = query(PPSQM_BY_ZONE_YEAR_SQL, {"keys": list(keys)}, engine)
    return apply_min_n(df, "clean_sales", ["median_ppsqm_aed"])


def rent_ppsqm_by_zone_year(keys: list[int] = HOMES, engine: Engine | None = None) -> pd.DataFrame:
    """Median new-contract rent per sq m by zone × year (min-n applied).

    Rows with ``zone`` NULL are the Dubai-wide figure for the year.
    """
    df = query(RENT_PPSQM_BY_ZONE_YEAR_SQL, {"keys": list(keys)}, engine)
    df["zone"] = df["zone"].fillna("Dubai (all zones)")
    return apply_min_n(df, "rent_n", ["median_rent_ppsqm_aed"])


def top_areas_by_value(snapshot, n: int = 10, engine: Engine | None = None) -> pd.DataFrame:
    """Top areas by market-sales value over the 12 calendar months to the snapshot month.

    The window is month-based (the snapshot month is partial), matching the "last 12
    months" section of reports/kpi_reconciliation.md; ``prior_value_aed`` is the 12
    months before it, for growth.
    """
    end_month = pd.Timestamp(snapshot).to_period("M").to_timestamp()
    start = end_month - pd.DateOffset(months=11)
    params = {
        "start": start.date(),
        "end": end_month.date(),
        "prev_start": (start - pd.DateOffset(months=12)).date(),
        "prev_end": (start - pd.DateOffset(months=1)).date(),
    }
    df = query(TOP_AREAS_SQL, params, engine)
    for col in ("market_value_aed", "prior_value_aed", "offplan_share_value"):
        df[col] = df[col].astype("float64")
    df["value_growth"] = df["market_value_aed"] / df["prior_value_aed"] - 1
    return df.head(n)


def mix_shift_inputs(
    property_type_key: int = config.RESIDENTIAL_APARTMENT_KEY, engine: Engine | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cell medians (year × zone × bedrooms) and the raw yearly median for one class."""
    params = {"ptk": property_type_key}
    cells = query(MIX_CELLS_SQL, params, engine)
    raw = query(MIX_RAW_SQL, params, engine)
    cells["median_ppsqm_aed"] = cells["median_ppsqm_aed"].astype("float64")
    raw = raw.astype({"median_ppsqm_aed": "float64", "offplan_share": "float64"})
    return cells, raw


def like_for_like(
    cells: pd.DataFrame, raw: pd.DataFrame, min_n: int = config.MIN_N
) -> pd.DataFrame:
    """Raw median change vs a like-for-like change, year on year.

    Like-for-like change from year t-1 to t = exp(Σ w·ln(m_t / m_t-1)) − 1 over the cells
    (zone × bedrooms within a class) with at least ``min_n`` sales in **both** years,
    weighted by year t-1 counts (a fixed-basket, Laspeyres-style comparison). Holding
    the basket fixed removes the effect of *which* homes sold; the raw median does not,
    so the gap between the two is the mix shift.

    Args:
        cells: ``year, zone, bedrooms, n, median_ppsqm_aed``.
        raw: ``year, n, median_ppsqm_aed`` (plus any extra columns, kept).
        min_n: Minimum sales per cell in both years.

    Returns:
        One row per year with ``raw_change``, ``lfl_change``, ``mix_effect`` (raw − lfl),
        ``cells_used`` and ``coverage`` (share of year-t sales inside the matched cells).
    """
    key = ["zone", "bedrooms"]
    rows = []
    for year in sorted(raw["year"])[1:]:
        prev = cells[(cells["year"] == year - 1) & (cells["n"] >= min_n)]
        cur = cells[(cells["year"] == year) & (cells["n"] >= min_n)]
        m = prev.merge(cur, on=key, suffixes=("_prev", "_cur"))
        total_cur = cells.loc[cells["year"] == year, "n"].sum()
        if m.empty:
            lfl = np.nan
        else:
            w = m["n_prev"] / m["n_prev"].sum()
            log_rel = np.log(m["median_ppsqm_aed_cur"] / m["median_ppsqm_aed_prev"])
            lfl = float(np.exp((w * log_rel).sum()) - 1)
        r_prev = raw.loc[raw["year"] == year - 1, "median_ppsqm_aed"].iloc[0]
        r_cur = raw.loc[raw["year"] == year, "median_ppsqm_aed"].iloc[0]
        raw_change = r_cur / r_prev - 1
        rows.append(
            {
                "year": year,
                "raw_change": raw_change,
                "lfl_change": lfl,
                "mix_effect": raw_change - lfl,
                "cells_used": len(m),
                "coverage": m["n_cur"].sum() / total_cur if total_cur else np.nan,
            }
        )
    out = pd.DataFrame(rows)
    return out.merge(raw.drop(columns=["n"], errors="ignore"), on="year", how="left")


def yield_preview_cells(snapshot, engine: Engine | None = None) -> pd.DataFrame:
    """Last-12-month median ready price and new rent per zone × class (× bedrooms).

    ``gross_yield`` = median annual rent ÷ median price, blanked where either side has
    fewer than 20 observations. Rows with ``is_rollup`` are the zone × class roll-up.
    PREVIEW ONLY: the Phase 4 yields use area × sub-type × bedrooms × quarter.
    """
    end = pd.Timestamp(snapshot)
    start = (end - pd.DateOffset(years=1) + pd.Timedelta(days=1)).date()
    params = {"keys": HOMES, "start": start, "end": end.date()}
    df = query(YIELD_PREVIEW_SQL, params, engine)
    df = df.astype({"median_price_aed": "float64", "median_annual_rent_aed": "float64"})
    df["gross_yield"] = df["median_annual_rent_aed"] / df["median_price_aed"]
    df = apply_min_n(df, ["sales_n", "rent_n"], ["gross_yield"])
    lo, hi = YIELD_SANITY
    df["is_outside_sanity"] = df["gross_yield"].notna() & ~df["gross_yield"].between(lo, hi)
    return df


def yield_by_zone(cells: pd.DataFrame) -> pd.DataFrame:
    """One gross yield per zone × class from ``yield_preview_cells``.

    Uses the sales-weighted mean of the bedroom cells that pass min-n on both sides
    (like-for-like: a 1-bed rent against a 1-bed price). Where no bedroom cell passes,
    it rolls up to the zone × class medians (min-n still applies); otherwise blank.
    Cells outside the ``YIELD_SANITY`` band are left out and counted in ``cells_flagged``.
    """
    rows = []
    for (zone, label), g in cells.groupby(["zone", "property_type_label"]):
        cells_ = g[(~g["is_rollup"]) & g["gross_yield"].notna()]
        ok = cells_[~cells_["is_outside_sanity"]]
        roll = g[g["is_rollup"] & ~g["is_outside_sanity"]]
        if not ok.empty:
            y = float(np.average(ok["gross_yield"], weights=ok["sales_n"]))
            method, n_sales, n_rent = "bedroom cells", ok["sales_n"].sum(), ok["rent_n"].sum()
        elif not roll.empty and roll["gross_yield"].notna().any():
            y = float(roll["gross_yield"].iloc[0])
            method, n_sales, n_rent = "zone roll-up", roll["sales_n"].sum(), roll["rent_n"].sum()
        else:
            y, method = np.nan, "below min-n"
            n_sales = roll["sales_n"].sum() if not roll.empty else 0
            n_rent = roll["rent_n"].sum() if not roll.empty else 0
        rows.append(
            {
                "zone": zone,
                "property_type_label": label,
                "gross_yield": y,
                "method": method,
                "sales_n": int(n_sales),
                "rent_n": int(n_rent),
                "cells_flagged": int(cells_["is_outside_sanity"].sum()),
            }
        )
    return pd.DataFrame(rows)


# Is a villa's procedure_area the plot or the built-up area? DLD doesn't say. Lines with a
# bedroom count look built-up (a 3-bed ~190 sq m); lines without look like plots (median
# ~550-600 sq m). The mix of the two shifts over time, which moves AED per sq m by itself.
AREA_BASIS_SQL = """
select property_type_key, extract(year from txn_date)::int as year, count(*) as clean_sales,
       avg((bedrooms is null)::int) as share_no_bedrooms,
       percentile_cont(0.5) within group (order by area_sqm) as median_area_sqm,
       percentile_cont(0.5) within group (order by area_sqm)
           filter (where bedrooms is not null) as median_area_with_bedrooms,
       percentile_cont(0.5) within group (order by area_sqm)
           filter (where bedrooms is null) as median_area_no_bedrooms,
       percentile_cont(0.5) within group (order by price_per_sqm_aed)
           filter (where bedrooms is not null) as median_ppsqm_with_bedrooms,
       percentile_cont(0.5) within group (order by actual_worth_aed) as median_price_aed
from gold.fct_transaction
where is_clean_market_sale and is_in_report_scope and property_type_key = any(:keys)
group by 1, 2
order by 1, 2
"""


def area_basis(keys: list[int] = HOMES, engine: Engine | None = None) -> pd.DataFrame:
    """Area basis per class × year: bedrooms-missing share, median areas, per-unit price.

    Columns: share of sales without bedrooms, median area with / without bedrooms, AED per
    sq m on the bedroom-known (built-up-like) subset, and the median price per unit.

    Used to test whether villa AED per sq m is comparable with apartments (it isn't when
    part of the villa areas are plots) and whether within-class growth is driven by a
    shift in the area basis.
    """
    df = query(AREA_BASIS_SQL, {"keys": list(keys)}, engine)
    return df.astype({c: "float64" for c in df.columns if c not in ("property_type_key", "year")})
