-- Conformed property type: every (source, usage, property type, sub-type) combination in
-- the data -> one dim_property_type key, so a single Power BI slicer filters sales, rents
-- and the aggregates alike (docs/06 §2; owner decision 2026-09-30).
--
-- DLD sales and Ejari rents describe property differently (DLD: Unit / Villa / Land /
-- Building x Flat / Office / Shop ...; Ejari: ~70 property types x layout sub-types), so
-- both are mapped to a shared vocabulary:
--   usage group    (seed_property_usage_map, by source usage label)
--   property class (seed_property_type_map, by type and sub-type; a blank sub-type in the
--                   seed is a wildcard used when no exact sub-type row exists)
-- property_type_key = usage_group_id * 100 + property_class_id, e.g. 101 = Residential x
-- Apartment. A missing source value maps to Unknown (9 / 99); a value present in the data
-- but absent from the seeds is caught by the is_*_mapped tests instead of hiding there.
--
-- The facts join on the *_join columns (NULL -> '') so Postgres can hash-join 10.5M rent
-- lines against this small table.

with combos as (

    select distinct 'transactions' as source, property_usage, property_type, property_sub_type
    from {{ ref('int_market_sales') }}
    union
    select distinct 'transactions', property_usage, property_type, property_sub_type
    from {{ ref('int_mortgages') }}
    union
    select distinct 'rents', property_usage, property_type, property_sub_type
    from {{ ref('int_rent_contracts') }}

),

resolved as (

    select
        c.*,
        u.usage_group_id,
        coalesce(exact.property_class, wildcard.property_class) as property_class
    from combos as c
    left join {{ ref('seed_property_usage_map') }} as u
        on u.source = c.source
        and u.property_usage = c.property_usage
    left join {{ ref('seed_property_type_map') }} as exact
        on exact.source = c.source
        and exact.property_type = c.property_type
        and exact.property_sub_type = c.property_sub_type
    left join {{ ref('seed_property_type_map') }} as wildcard
        on wildcard.source = c.source
        and wildcard.property_type = c.property_type
        and wildcard.property_sub_type is null

)

select
    r.source,
    r.property_usage,
    r.property_type,
    r.property_sub_type,
    coalesce(r.property_usage, '') as property_usage_join,
    coalesce(r.property_type, '') as property_type_join,
    coalesce(r.property_sub_type, '') as property_sub_type_join,
    coalesce(r.usage_group_id, 9) as usage_group_id,
    coalesce(pc.property_class_id, 99) as property_class_id,
    coalesce(r.usage_group_id, 9) * 100 + coalesce(pc.property_class_id, 99) as property_type_key,
    -- A source label that exists but isn't in the seeds is a mapping gap (tested).
    r.property_usage is null or r.usage_group_id is not null as is_usage_mapped,
    r.property_type is null or pc.property_class_id is not null as is_type_mapped
from resolved as r
left join {{ ref('seed_property_class') }} as pc
    on pc.property_class = r.property_class
