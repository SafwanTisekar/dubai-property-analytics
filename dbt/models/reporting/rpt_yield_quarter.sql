{{ config(alias='yield_quarter', tags=['post_ml']) }}

-- Gross rental yields (docs/05 §3): median annual rent of new single-line market contracts
-- (rule C11) / median price of clean ready sales, same cell. Area rows and zone rows
-- ("Geo Level"): only cells with min_n observations on both sides were written; an area
-- cell below that is represented only in its zone row ("Areas Rolled Up"). Gross: before
-- service charges, vacancy and fees. "Is Outside Sanity Band" = outside 2-15%.
select
    y.quarter_start as "Quarter Start",
    initcap(y.geo_level) as "Geo Level",
    y.zone as "Zone",
    y.area_key as "Area Key",
    y.property_type_key as "Property Type Key",
    y.bedrooms as "Bedrooms",
    y.n_rent as "Rent Contracts",
    y.n_sale as "Sales",
    {{ rpt_aed('y.median_annual_rent_aed') }} as "Median Annual Rent AED",
    {{ rpt_aed('y.median_price_aed') }} as "Median Price AED",
    round(y.gross_yield, 4) as "Gross Yield",
    y.is_outside_sanity as "Is Outside Sanity Band",
    y.areas_rolled_up as "Areas Rolled Up",
    y.is_partial_period as "Is Partial Period"
from {{ source('ml', 'agg_yield_quarter') }} as y
where y.model_version = '{{ var("yield_model_version") }}'
