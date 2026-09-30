-- Every additive column of agg_rent_month equals the same measure over fct_rent_contract in
-- the reporting scope, and the lines left out are exactly the C18 date exclusions (invalid
-- start, pre-2004 start, start after the data snapshot). Returns a row per broken check.
with fct as (
    select
        count(*) filter (where is_in_report_scope) as lines,
        count(*) filter (where is_in_report_scope and line_number = 1) as contracts,
        sum(annual_rent_alloc_aed) filter (where is_in_report_scope) as rent_alloc,
        count(*) filter (where is_in_report_scope and is_rent_comparable) as comparable,
        count(*) filter (where is_in_report_scope and is_market_rent) as market_rent,
        sum(annual_rent_contract_aed) filter (where is_in_report_scope and is_rent_comparable)
            as comparable_rent,
        count(*) filter (
            where is_in_report_scope and is_rent_comparable and rent_per_sqm_aed is not null
        ) as sqm_n,
        sum(area_sqm) filter (
            where is_in_report_scope and is_rent_comparable and rent_per_sqm_aed is not null
        ) as comparable_area,
        count(*) filter (where not is_in_report_scope) as out_of_scope,
        count(*) filter (
            where is_date_invalid or is_start_after_snapshot
                or start_date < date '{{ var("dim_date_start") }}'
        ) as logged_exclusions
    from {{ ref('fct_rent_contract') }}
),

agg as (
    select
        sum(rent_lines) as lines,
        sum(contracts) as contracts,
        sum(annual_rent_alloc_aed) as rent_alloc,
        sum(comparable_contracts) as comparable,
        sum(market_rent_contracts) as market_rent,
        sum(sum_annual_rent_aed) as comparable_rent,
        sum(rent_per_sqm_n) as sqm_n,
        sum(comparable_area_sqm) as comparable_area
    from {{ ref('agg_rent_month') }}
)

select 'agg vs fct' as check_name, f.lines as fct_lines, a.lines as agg_lines
from fct as f cross join agg as a
where f.lines <> a.lines
   or f.contracts <> a.contracts
   or f.rent_alloc is distinct from a.rent_alloc
   or f.comparable <> a.comparable
   or f.market_rent <> a.market_rent
   or coalesce(f.comparable_rent, 0) <> a.comparable_rent
   or f.sqm_n <> a.sqm_n
   or coalesce(f.comparable_area, 0) <> a.comparable_area
union all
select 'out of scope = C18 exclusions', out_of_scope, logged_exclusions
from fct
where out_of_scope <> logged_exclusions
