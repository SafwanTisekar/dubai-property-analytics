{{ config(tags=['post_ml']) }}

-- Stress test sanity (docs/05 §4): within a segment and loan basis, a deeper shock can only
-- add buyers in negative equity (and AED of it), and so can a higher assumed LTV at the
-- same shock. Same population on both sides, so any violation is a bug. Rows returned fail.
with g as (
    select *
    from {{ source('ml', 'stress_grid') }}
    where model_version = '{{ var("stress_model_version") }}' and scenario = 'grid' and is_published
),

by_shock as (
    select *,
        lag(negative_equity_count) over w as prev_count,
        lag(negative_equity_aed) over w as prev_aed
    from g
    window w as (
        partition by segment_level, property_type_key, zone, area_key, is_offplan, ltv_basis,
            ltv_pct
        order by shock_pct desc
    )
),

by_ltv as (
    select *,
        lag(negative_equity_count) over w as prev_count,
        lag(negative_equity_aed) over w as prev_aed
    from g
    where ltv_basis = 'grid'
    window w as (
        partition by segment_level, property_type_key, zone, area_key, is_offplan, shock_pct
        order by ltv_pct
    )
)

select 'shock' as direction, segment_level, property_type_key, zone, area_key, shock_pct, ltv_pct
from by_shock
where negative_equity_count < prev_count or negative_equity_aed < prev_aed - 0.01
union all
select 'ltv', segment_level, property_type_key, zone, area_key, shock_pct, ltv_pct
from by_ltv
where negative_equity_count < prev_count or negative_equity_aed < prev_aed - 0.01
