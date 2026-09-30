{{
    config(
        indexes=[
            {'columns': ['month']},
            {'columns': ['area_key']},
        ]
    )
}}

-- Sales and financing by month x area x conformed property type x bedrooms x off-plan flag,
-- over the reporting scope (fct_transaction.is_in_report_scope). Every count and AED column
-- is additive, so Power BI can sum them to any level; recon_agg_area_month_vs_fct checks
-- each total against the fact.
--
-- Populations (docs/01 §4):
--   market sales       is_market_sale; AED once per deal (C16)
--   clean sales        is_clean_market_sale: the price population (medians)
--   area-weighted      clean sales whose area is within the class cap
--                      (not is_area_above_class_cap): Σ value / Σ sq m, per property type
--   purchase mortgages ready market sales matched to a same-day purchase mortgage
--                      (has_purchase_mortgage, counted on the sale line so it sits in the
--                      sale's cell): ÷ ready market sales = purchase-mortgage share
--   new mortgages      is_new_mortgage (individual; includes refinancing). Secondary
--                      indicator: new mortgages per 100 market sales. Loans only where
--                      the amount is a verified loan (C10), once per deal
--   portfolio          is_portfolio_mortgage, reported apart from the share: deals = lead
--                      lines (so deals add up), value once per deal
--
-- Medians are kept for every cell with their n (clean_sales). The min-n rule (n >= 20) is
-- applied when publishing, in rpt.area_month; the Σ value / Σ area columns give an exact
-- area-weighted AED per sq m at any rollup.

select
    date_trunc('month', txn_date)::date as month,
    area_key,
    property_type_key,
    bedrooms,
    is_offplan,

    count(*) as transaction_lines,
    sum(aed_counted_once) as aed_counted_once,

    count(*) filter (where is_market_sale) as market_sales,
    coalesce(sum(aed_counted_once) filter (where is_market_sale), 0) as market_sales_value_aed,

    count(*) filter (where is_clean_market_sale) as clean_sales,
    -- Area-weighted population: clean sales with a plausible area for the class.
    count(*) filter (where is_clean_market_sale and not is_area_above_class_cap)
        as clean_sales_aw_n,
    coalesce(
        sum(aed_counted_once) filter (where is_clean_market_sale and not is_area_above_class_cap),
        0
    ) as clean_sales_value_aed,
    coalesce(
        sum(area_sqm) filter (where is_clean_market_sale and not is_area_above_class_cap), 0
    ) as clean_sales_area_sqm,
    coalesce(sum(price_per_sqm_aed) filter (where is_clean_market_sale), 0) as sum_price_per_sqm_aed,
    round(
        (percentile_cont(0.5) within group (order by price_per_sqm_aed)
            filter (where is_clean_market_sale))::numeric,
        2
    ) as median_price_per_sqm_aed,
    round(
        (percentile_cont(0.5) within group (order by aed_counted_once)
            filter (where is_clean_market_sale))::numeric,
        2
    ) as median_price_aed,

    count(*) filter (where has_purchase_mortgage) as purchase_mortgages,
    count(*) filter (where is_new_mortgage) as new_mortgages,
    coalesce(sum(mortgage_amount_once_aed) filter (where is_new_mortgage), 0) as new_mortgage_loans_aed,

    count(*) filter (where is_portfolio_mortgage and is_deal_group_lead) as portfolio_mortgage_deals,
    count(*) filter (where is_portfolio_mortgage) as portfolio_mortgage_lines,
    coalesce(sum(portfolio_mortgage_value_once_aed), 0) as portfolio_mortgage_value_aed
from {{ ref('fct_transaction') }}
where is_in_report_scope
group by 1, 2, 3, 4, 5
