-- Every additive column of agg_area_month equals the same measure over fct_transaction in
-- the reporting scope, and the lines left out of scope are exactly the logged exclusions
-- (pre-2004 or no valid date, C18). Returns a row per broken check.
with fct as (
    select
        count(*) filter (where is_in_report_scope) as lines,
        sum(aed_counted_once) filter (where is_in_report_scope) as aed_once,
        count(*) filter (where is_in_report_scope and is_market_sale) as market_sales,
        sum(aed_counted_once) filter (where is_in_report_scope and is_market_sale) as market_value,
        count(*) filter (where is_in_report_scope and is_clean_market_sale) as clean_sales,
        count(*) filter (
            where is_in_report_scope and is_clean_market_sale and not is_area_above_class_cap
        ) as aw_n,
        sum(aed_counted_once) filter (
            where is_in_report_scope and is_clean_market_sale and not is_area_above_class_cap
        ) as clean_value,
        sum(area_sqm) filter (
            where is_in_report_scope and is_clean_market_sale and not is_area_above_class_cap
        ) as clean_area,
        count(*) filter (where is_in_report_scope and is_new_mortgage) as new_mortgages,
        sum(mortgage_amount_once_aed) filter (where is_in_report_scope and is_new_mortgage) as loans,
        count(*) filter (where is_in_report_scope and is_portfolio_mortgage and is_deal_group_lead)
            as portfolio_deals,
        count(*) filter (where is_in_report_scope and is_portfolio_mortgage) as portfolio_lines,
        sum(portfolio_mortgage_value_once_aed) filter (where is_in_report_scope) as portfolio_value,
        count(*) filter (where not is_in_report_scope) as out_of_scope,
        count(*) filter (where is_pre_2004 or is_date_invalid) as logged_exclusions
    from {{ ref('fct_transaction') }}
),

agg as (
    select
        sum(transaction_lines) as lines,
        sum(aed_counted_once) as aed_once,
        sum(market_sales) as market_sales,
        sum(market_sales_value_aed) as market_value,
        sum(clean_sales) as clean_sales,
        sum(clean_sales_aw_n) as aw_n,
        sum(clean_sales_value_aed) as clean_value,
        sum(clean_sales_area_sqm) as clean_area,
        sum(new_mortgages) as new_mortgages,
        sum(new_mortgage_loans_aed) as loans,
        sum(portfolio_mortgage_deals) as portfolio_deals,
        sum(portfolio_mortgage_lines) as portfolio_lines,
        sum(portfolio_mortgage_value_aed) as portfolio_value
    from {{ ref('agg_area_month') }}
)

select 'agg vs fct' as check_name, f.lines as fct_lines, a.lines as agg_lines
from fct as f cross join agg as a
where f.lines <> a.lines
   or f.aed_once is distinct from a.aed_once
   or f.market_sales <> a.market_sales
   or coalesce(f.market_value, 0) <> a.market_value
   or f.clean_sales <> a.clean_sales
   or f.aw_n <> a.aw_n
   or coalesce(f.clean_value, 0) <> a.clean_value
   or coalesce(f.clean_area, 0) <> a.clean_area
   or f.new_mortgages <> a.new_mortgages
   or coalesce(f.loans, 0) <> a.loans
   or f.portfolio_deals <> a.portfolio_deals
   or f.portfolio_lines <> a.portfolio_lines
   or coalesce(f.portfolio_value, 0) <> a.portfolio_value
union all
select 'out of scope = C18 exclusions', out_of_scope, logged_exclusions
from fct
where out_of_scope <> logged_exclusions
