"""Q2: how much of the market is financed, and has that shifted with interest rates?

* **Mortgage share** (docs/01 §4) = individual new mortgages ÷ (new mortgages + market
  sales), by month, from ``gold.agg_area_month``. Portfolio mortgages are outside the
  ratio and reported separately, one count per deal (C16).
* **Rates.** EIBOR is not loaded yet (docs/08 Phase 1), so the effective Fed Funds rate
  stands in: the dirham is pegged to the US dollar, so UAE policy rates track the Fed.
  Any link to mortgage share is an association, not a causal estimate.
* **Observed LTV.** The Phase 1 same-day match (phase1_findings §2), rebuilt on gold: a
  Mortgage Registration and a Sell (or Delayed Mortgage and Delayed Sell) on the same day
  for the same unit (area, building, project, sq m, rooms, type, sub-type), where the key
  is unique on both sides. LTV = loan ÷ sale price. It covers purchase mortgages only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import Engine

from dubai_property.analysis.common import query

MORTGAGE_SHARE_MONTHLY_SQL = """
with m as (
    select month, sum(new_mortgages) as new_mortgages, sum(market_sales) as market_sales,
           sum(new_mortgage_loans_aed) as new_mortgage_loans_aed
    from gold.agg_area_month
    where month between :start and :end
    group by month
)
select m.*, r.fed_funds_rate
from m
left join gold.fct_rates_monthly as r using (month)
order by month
"""

PORTFOLIO_BY_YEAR_SQL = """
select extract(year from month)::int as year,
       sum(portfolio_mortgage_deals) as portfolio_deals,
       sum(portfolio_mortgage_lines) as portfolio_lines,
       sum(portfolio_mortgage_value_aed) as portfolio_value_aed,
       sum(new_mortgages) as new_mortgages,
       sum(new_mortgage_loans_aed) as new_mortgage_loans_aed
from gold.agg_area_month
where month between :start and :end
group by 1
order by 1
"""

# Pairs of (mortgage procedure, sale procedure) whose amounts are a loan and a price (C10).
_PAIRS = "('Mortgage Registration', 'Sell'), ('Delayed Mortgage', 'Delayed Sell')"

LTV_PAIRS_CTE = f"""
with base as (
    select txn_date, area_key, coalesce(building_name, '') as building, project_key,
           area_sqm, coalesce(rooms_en, '') as rooms, coalesce(property_type, '') as ptype,
           coalesce(property_sub_type, '') as sub_type, procedure_name, actual_worth_aed,
           case when trans_group = 'Sales' then 'sale' else 'mortgage' end as side
    from gold.fct_transaction
    where is_in_report_scope
      and procedure_name in ('Mortgage Registration', 'Delayed Mortgage', 'Sell', 'Delayed Sell')
),
keyed as (
    select *, count(*) over (
        partition by txn_date, area_key, building, project_key, area_sqm, rooms, ptype,
                     sub_type, side) as lines_on_key
    from base
),
pairs as (
    select m.txn_date, m.actual_worth_aed / nullif(s.actual_worth_aed, 0) as ltv
    from keyed as m
    join keyed as s
        using (txn_date, area_key, building, project_key, area_sqm, rooms, ptype, sub_type)
    where m.side = 'mortgage' and s.side = 'sale'
      and m.lines_on_key = 1 and s.lines_on_key = 1
      and (m.procedure_name, s.procedure_name) in ({_PAIRS})
)
"""

LTV_BY_YEAR_SQL = (
    LTV_PAIRS_CTE
    + """
select extract(year from txn_date)::int as year, count(*) as pairs,
       percentile_cont(0.25) within group (order by ltv) as p25,
       percentile_cont(0.50) within group (order by ltv) as median,
       percentile_cont(0.75) within group (order by ltv) as p75,
       avg((ltv between 0.745 and 0.755)::int) as share_at_0_75,
       avg((ltv between 0.795 and 0.805)::int) as share_at_0_80,
       avg((ltv between 0.8475 and 0.8485)::int) as share_at_0_848,
       avg((ltv > 0.805 and ltv <= 1.0)::int) as share_0_80_to_1,
       avg((ltv > 1.001)::int) as share_above_1
from pairs
group by 1
order by 1
"""
)

# 0.025-wide bins from 0.40 to 1.10 (bucket 0 = below, 29 = above), per year.
LTV_HISTOGRAM_SQL = (
    LTV_PAIRS_CTE
    + """
select extract(year from txn_date)::int as year,
       width_bucket(ltv, 0.40, 1.10, 28) as bucket, count(*) as pairs
from pairs
where extract(year from txn_date) = any(:years)
group by 1, 2
order by 1, 2
"""
)


def mortgage_share_monthly(start, end, engine: Engine | None = None) -> pd.DataFrame:
    """Monthly mortgage share with a trailing 12-month version and the Fed Funds rate.

    The 12-month share is Σ mortgages ÷ Σ (mortgages + sales) over the window, not a
    mean of monthly ratios, so busy months weigh more.
    """
    df = query(MORTGAGE_SHARE_MONTHLY_SQL, {"start": start, "end": end}, engine)
    df["month"] = pd.to_datetime(df["month"])
    for col in ("new_mortgages", "market_sales", "new_mortgage_loans_aed", "fed_funds_rate"):
        df[col] = df[col].astype("float64")
    denom = df["new_mortgages"] + df["market_sales"]
    df["mortgage_share"] = df["new_mortgages"] / denom
    roll_m = df["new_mortgages"].rolling(12, min_periods=12).sum()
    roll_d = denom.rolling(12, min_periods=12).sum()
    df["mortgage_share_12m"] = roll_m / roll_d
    return df


def share_rate_correlation(df: pd.DataFrame, from_year: int = 2010) -> dict[str, float]:
    """Pearson correlation of the 12-month mortgage share with Fed Funds.

    Returns correlations in levels and in 12-month changes (changes remove the common
    trend that makes two slow series look related). Months before ``from_year`` are
    dropped: 2004–09 volumes are distorted by registration timing (see market_cycles).
    """
    d = df.loc[df["month"].dt.year >= from_year, ["mortgage_share_12m", "fed_funds_rate"]]
    d = d.dropna()
    diff = d.diff(12).dropna()
    return {
        "months": float(len(d)),
        "corr_levels": float(d.corr().iloc[0, 1]),
        "corr_12m_changes": float(diff.corr().iloc[0, 1]),
    }


def portfolio_by_year(start, end, engine: Engine | None = None) -> pd.DataFrame:
    """Portfolio mortgage deals / lines / value (once per deal) next to individual loans."""
    df = query(PORTFOLIO_BY_YEAR_SQL, {"start": start, "end": end}, engine)
    return df.astype({c: "float64" for c in df.columns if c != "year"})


def ltv_by_year(engine: Engine | None = None) -> pd.DataFrame:
    """Observed LTV (loan ÷ same-day sale price) percentiles and cap shares by year."""
    df = query(LTV_BY_YEAR_SQL, engine=engine)
    return df.astype({c: "float64" for c in df.columns if c not in ("year", "pairs")})


def ltv_histogram(years: list[int], engine: Engine | None = None) -> pd.DataFrame:
    """Observed-LTV histogram (0.025 bins, 0.40–1.10) for the given years, as shares.

    Returns one row per year × bin with ``ltv_low`` (the bin's lower edge; below 0.40
    and above 1.10 are the two open-ended buckets) and ``share`` of that year's pairs.
    """
    df = query(LTV_HISTOGRAM_SQL, {"years": list(years)}, engine)
    width = (1.10 - 0.40) / 28
    df["ltv_low"] = np.round(0.40 + (df["bucket"] - 1) * width, 3)
    df["share"] = df["pairs"] / df.groupby("year")["pairs"].transform("sum")
    return df
