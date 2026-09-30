{{ config(alias='area_month') }}

-- Monthly sales and financing by area x property type x bedrooms x off-plan. Counts and AED
-- add up to any level. Medians appear only where n >= min_n (CLAUDE.md); for rollups use
-- the area-weighted "Clean Sales Value AED" / "Clean Sales Area Sq M" (clean sales with an
-- area within the class cap, n = "Clean Sales AW N"), within a property class: across
-- classes it mixes land, buildings and units.
select
    month as "Month",
    area_key as "Area Key",
    property_type_key as "Property Type Key",
    bedrooms as "Bedrooms",
    is_offplan as "Is Off-Plan",

    market_sales as "Market Sales",
    {{ rpt_aed('market_sales_value_aed') }} as "Market Sales Value AED",
    clean_sales as "Clean Sales",
    clean_sales_aw_n as "Clean Sales AW N",
    {{ rpt_aed('clean_sales_value_aed') }} as "Clean Sales Value AED",
    round(clean_sales_area_sqm, 2) as "Clean Sales Area Sq M",
    {{ rpt_min_n_median('median_price_per_sqm_aed', 'clean_sales') }} as "Median Price per Sq M AED",
    {{ rpt_min_n_median('median_price_aed', 'clean_sales') }} as "Median Price AED",

    new_mortgages as "New Mortgages",
    {{ rpt_aed('new_mortgage_loans_aed') }} as "New Mortgage Loans AED",
    portfolio_mortgage_deals as "Portfolio Mortgage Deals",
    portfolio_mortgage_lines as "Portfolio Mortgage Lines",
    {{ rpt_aed('portfolio_mortgage_value_aed') }} as "Portfolio Mortgage Value AED"
from {{ ref('agg_area_month') }}
