-- Conformed property type: usage group x property class, shared by fct_transaction,
-- fct_rent_contract, agg_area_month and agg_rent_month (int_property_type_lookup maps the
-- source labels). Every combination is listed, even unused ones, so the key set is fixed
-- by the seeds and not by what a snapshot happens to contain.
-- property_type_key = usage_group_id * 100 + property_class_id (e.g. 101 = Residential x
-- Apartment); 999 = Unknown x Unknown.

with usage_groups as (

    select distinct usage_group_id, usage_group
    from {{ ref('seed_property_usage_map') }}
    union all
    select 9, 'Unknown'

)

select
    u.usage_group_id * 100 + c.property_class_id as property_type_key,
    u.usage_group_id,
    u.usage_group,
    c.property_class_id,
    c.property_class,
    u.usage_group || ' · ' || c.property_class as property_type_label,
    c.description as property_class_description
from usage_groups as u
cross join {{ ref('seed_property_class') }} as c
