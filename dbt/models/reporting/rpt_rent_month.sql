{{ config(alias='rent_month') }}

-- Monthly rents by area x property type x bedrooms x new/renewal: the only rent table in
-- Power BI (no contract detail, CLAUDE.md). "Market Rent Contracts" = new comparable
-- contracts (the default market rent). Medians appear only where n >= min_n; for rollups
-- use the sums (Σ rent / Σ area for an area-weighted rent per sq m, within a property
-- class). Contracts starting after the data snapshot date are not included.
select
    month as "Month",
    area_key as "Area Key",
    property_type_key as "Property Type Key",
    bedrooms as "Bedrooms",
    is_new as "Is New Contract",

    rent_lines as "Rent Lines",
    contracts as "Contracts",
    {{ rpt_aed('annual_rent_alloc_aed') }} as "Annual Rent AED",
    comparable_contracts as "Comparable Contracts",
    market_rent_contracts as "Market Rent Contracts",
    {{ rpt_aed('sum_annual_rent_aed') }} as "Comparable Annual Rent AED",
    {{ rpt_min_n_median('median_annual_rent_aed', 'comparable_contracts') }} as "Median Annual Rent AED",
    rent_per_sqm_n as "Rent per Sq M N",
    {{ rpt_min_n_median('median_rent_per_sqm_aed', 'rent_per_sqm_n') }} as "Median Rent per Sq M AED",
    round(comparable_area_sqm, 2) as "Comparable Area Sq M",
    {{ rpt_aed('comparable_rent_with_area_aed') }} as "Comparable Rent with Area AED"
from {{ ref('agg_rent_month') }}
