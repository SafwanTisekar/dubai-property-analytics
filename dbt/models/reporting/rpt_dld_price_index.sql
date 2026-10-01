{{ config(alias='dld_price_index') }}

-- DLD's official Residential Sale Index (monthly), for the "ours vs DLD" line on the Prices
-- page (docs/05 §2 validation). Rebased to the hedonic index base month (Jan 2019 = 100) so
-- both lines share an axis; "Segment" uses rpt.price_index's labels so one slicer drives
-- both. DLD's file ends in May 2024. Ours leads DLD by ~6 months (reports/price_index.md):
-- compare turning points with that in mind, not month for month.
with monthly as (
    select
        month_start,
        case segment
            when 'all' then 'Dubai (all residential)'
            when 'flat' then 'Apartments'
            when 'villa' then 'Villas / Townhouses'
        end as segment,
        index_ratio
    from {{ ref('stg_dld_price_index') }}
    where frequency = 'monthly'
),

base as (
    select segment, index_ratio as base_ratio
    from monthly
    where month_start = date '{{ var("index_base_month") }}'
)

select
    m.segment as "Segment",
    m.month_start as "Period Start",
    round(m.index_ratio * 100 / b.base_ratio, 2) as "DLD Index Value",
    round(
        m.index_ratio / lag(m.index_ratio, 12) over (partition by m.segment order by m.month_start) - 1,
        4
    ) as "DLD YoY Change"
from monthly as m
inner join base as b using (segment)
