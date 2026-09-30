{{
    config(
        indexes=[
            {'columns': ['month']},
            {'columns': ['area_key']},
        ]
    )
}}

-- Rents by month (contract start) x area x conformed property type x bedrooms x new/renewal,
-- over the reporting scope. The only rent table Power BI imports: the 10.5M contract lines
-- stay in Postgres (CLAUDE.md). Counts and AED columns are additive; recon_agg_rent_month_vs_fct
-- checks each total against fct_rent_contract.
--
-- Populations:
--   all lines          rent_lines, contracts (counted on line 1, so they add up), and
--                      annual_rent_alloc_aed (C11: each contract counted once)
--   comparable         is_rent_comparable: single-line, market property type, inside the
--                      C14 band, usable dates. Medians and sums for rent levels
--   market rent        comparable and new (is_market_rent, C13): the default market rent;
--                      with is_new in the grain it is the is_new = true rows
--
-- Medians are kept for every cell with their n; rpt.rent_month applies the min-n rule.
-- comparable_rent_with_area_aed / comparable_area_sqm is the exact area-weighted rent per
-- sq m at any rollup (only lines with a real area, C21).

select
    date_trunc('month', start_date)::date as month,
    area_key,
    property_type_key,
    bedrooms,
    is_new,

    count(*) as rent_lines,
    count(*) filter (where line_number = 1) as contracts,
    sum(annual_rent_alloc_aed) as annual_rent_alloc_aed,

    count(*) filter (where is_rent_comparable) as comparable_contracts,
    count(*) filter (where is_market_rent) as market_rent_contracts,
    coalesce(sum(annual_rent_contract_aed) filter (where is_rent_comparable), 0)
        as sum_annual_rent_aed,
    round(
        (percentile_cont(0.5) within group (order by annual_rent_contract_aed)
            filter (where is_rent_comparable))::numeric,
        2
    ) as median_annual_rent_aed,

    count(*) filter (where is_rent_comparable and rent_per_sqm_aed is not null) as rent_per_sqm_n,
    coalesce(sum(rent_per_sqm_aed) filter (where is_rent_comparable), 0) as sum_rent_per_sqm_aed,
    round(
        (percentile_cont(0.5) within group (order by rent_per_sqm_aed)
            filter (where is_rent_comparable and rent_per_sqm_aed is not null))::numeric,
        2
    ) as median_rent_per_sqm_aed,
    coalesce(sum(area_sqm) filter (where is_rent_comparable and rent_per_sqm_aed is not null), 0)
        as comparable_area_sqm,
    coalesce(
        sum(annual_rent_contract_aed) filter (where is_rent_comparable and rent_per_sqm_aed is not null),
        0
    ) as comparable_rent_with_area_aed
from {{ ref('fct_rent_contract') }}
where is_in_report_scope
group by 1, 2, 3, 4, 5
