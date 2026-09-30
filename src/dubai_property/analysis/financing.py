"""Q2: how much of the market is financed, and has that shifted with interest rates?

* **Purchase-mortgage share of ready sales** (docs/01 §4, the headline) = ready market
  sales matched to a same-day purchase mortgage of the same unit
  (``fct_transaction.has_purchase_mortgage``, from ``int_purchase_mortgage_pairs``) ÷ ready
  market sales. The DLD register doesn't link a sale to its loan; a mortgaged purchase
  registers both a sale and a mortgage line, and new mortgages include refinancing, so
  "mortgages ÷ (mortgages + sales)" double-counts. The match is a **lower bound**: a loan
  registered on another day or keyed differently isn't matched.
* **Upper bound**: every Mortgage Registration / Delayed Mortgage line (the ready-unit
  loans, excluding inferred portfolio lines) ÷ ready market sales. It includes refinancing
  and loans on units bought earlier, so the true share lies between the two. The **match
  rate** (matched ÷ those loans) rose over time, so part of the lower bound's trend is
  better matching, not more borrowing.
* **New mortgages per 100 market sales** is the secondary indicator (all individual new
  mortgages, including off-plan pre-registration and refinancing).
* Off-plan buyers mostly pay the developer in instalments; a sale with no mortgage is
  "not bank-financed at registration", not necessarily a cash purchase.
* **Rates.** EIBOR is not loaded yet (docs/08 Phase 1), so the effective Fed Funds rate
  stands in: the dirham is pegged to the US dollar. Associations only.
* **Observed LTV** = loan ÷ price on the matched pairs (``fct_transaction.purchase_ltv``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import Engine

from dubai_property.analysis.common import query

# Monthly, grouped in SQL over the fact (the counts match gold.agg_area_month; the upper
# bound needs the procedure, which the aggregate doesn't carry).
MORTGAGE_INDICATORS_MONTHLY_SQL = """
with m as (
    select date_trunc('month', txn_date)::date as month,
           count(*) filter (where is_market_sale) as market_sales,
           count(*) filter (where is_market_sale and not is_offplan) as ready_sales,
           count(*) filter (where has_purchase_mortgage) as purchase_mortgages,
           count(*) filter (where is_new_mortgage) as new_mortgages,
           count(*) filter (
               where procedure_name in ('Mortgage Registration', 'Delayed Mortgage')
                 and not is_repeated_deal_value
           ) as ready_unit_mortgages
    from gold.fct_transaction
    where is_in_report_scope and txn_date between :start and :end
    group by 1
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

LTV_BY_YEAR_SQL = """
with pairs as (
    select txn_date, purchase_ltv as ltv
    from gold.fct_transaction
    where is_purchase_mortgage and is_in_report_scope
)
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

# 0.025-wide bins from 0.40 to 1.10 (bucket 0 = below, 29 = above), per year.
LTV_HISTOGRAM_SQL = """
select extract(year from txn_date)::int as year,
       width_bucket(purchase_ltv, 0.40, 1.10, 28) as bucket, count(*) as pairs
from gold.fct_transaction
where is_purchase_mortgage and is_in_report_scope
  and extract(year from txn_date) = any(:years)
group by 1, 2
order by 1, 2
"""


_COUNTS = (
    "market_sales",
    "ready_sales",
    "purchase_mortgages",
    "new_mortgages",
    "ready_unit_mortgages",
)


def _indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add the ratios to a frame of summed counts (any grain)."""
    df["purchase_share"] = df["purchase_mortgages"] / df["ready_sales"]
    df["upper_share"] = df["ready_unit_mortgages"] / df["ready_sales"]
    df["match_rate"] = df["purchase_mortgages"] / df["ready_unit_mortgages"]
    df["new_per_100_sales"] = 100 * df["new_mortgages"] / df["market_sales"]
    return df


def mortgage_indicators_monthly(start, end, engine: Engine | None = None) -> pd.DataFrame:
    """Monthly purchase-mortgage share (and its upper bound) with Fed Funds.

    ``purchase_share_12m`` is Σ matched ÷ Σ ready sales over the trailing 12 months (a
    ratio of sums, so busy months weigh more), used for the rate comparison.
    """
    df = query(MORTGAGE_INDICATORS_MONTHLY_SQL, {"start": start, "end": end}, engine)
    df["month"] = pd.to_datetime(df["month"])
    for col in (*_COUNTS, "fed_funds_rate"):
        df[col] = df[col].astype("float64")
    df = _indicators(df)
    roll = df[list(_COUNTS)].rolling(12, min_periods=12).sum()
    df["purchase_share_12m"] = roll["purchase_mortgages"] / roll["ready_sales"]
    df["upper_share_12m"] = roll["ready_unit_mortgages"] / roll["ready_sales"]
    df["new_per_100_sales_12m"] = 100 * roll["new_mortgages"] / roll["market_sales"]
    return df


def mortgage_indicators_by_year(monthly: pd.DataFrame) -> pd.DataFrame:
    """Yearly sums of ``mortgage_indicators_monthly`` with the ratios recomputed."""
    y = monthly.groupby(monthly["month"].dt.year)[list(_COUNTS)].sum()
    y.index.name = "year"
    y = _indicators(y.reset_index())
    rate = monthly.groupby(monthly["month"].dt.year)["fed_funds_rate"].mean()
    return y.merge(rate.rename("fed_funds_avg"), left_on="year", right_index=True)


def share_rate_correlation(
    df: pd.DataFrame, from_year: int = 2010, col: str = "purchase_share_12m"
) -> dict[str, float]:
    """Pearson correlation of a trailing-12-month share with Fed Funds.

    Returns correlations in levels and in 12-month changes (changes remove the common
    trend that makes two slow series look related). Months before ``from_year`` are
    dropped: 2004–09 volumes are distorted by registration timing (see market_cycles).
    """
    d = df.loc[df["month"].dt.year >= from_year, [col, "fed_funds_rate"]].dropna()
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


# Monthly shares of matched purchase mortgages sitting at the regulatory caps, to date the
# 2020 change (CBUAE Board Resolution 31/2/2020, effective 2020-04-08; seed_ltv_rules).
LTV_CLUSTERS_MONTHLY_SQL = """
select date_trunc('month', txn_date)::date as month, count(*) as pairs,
       avg((purchase_ltv between 0.745 and 0.755)::int) as share_at_0_75,
       avg((purchase_ltv between 0.795 and 0.805)::int) as share_at_0_80,
       avg((purchase_ltv between 0.8475 and 0.8485)::int) as share_at_0_848,
       avg((purchase_ltv between 0.845 and 0.855)::int) as share_0_845_to_0_855
from gold.fct_transaction
where is_purchase_mortgage and txn_date between :start and :end
group by 1
order by 1
"""


def ltv_cluster_shares_monthly(start, end, engine: Engine | None = None) -> pd.DataFrame:
    """Monthly share of matched purchase mortgages at exactly 75%, 80% and 84.8% LTV."""
    df = query(LTV_CLUSTERS_MONTHLY_SQL, {"start": start, "end": end}, engine)
    df["month"] = pd.to_datetime(df["month"])
    return df.astype({c: "float64" for c in df.columns if c.startswith("share")})
