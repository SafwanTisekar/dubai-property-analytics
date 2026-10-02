{{ config(severity='warn') }}
-- C8 name drift: warn when DLD publishes a different name for an area_id than seed_area.
-- A rename is fine (the id is the key), but the seed should be updated to match. Reads the
-- distinct (id, name) pairs straight from bronze, which is cheaper than the rent view.
-- The seed may add a clarification in brackets to DLD's name (Phase 5: "Island 2 (Jumeira
-- Bay)"); the published name must still match the seed name without it.
with published as (
    select 'transactions' as source, area_id, area_name_en, count(*) as lines
    from {{ source('bronze', 'dld_transactions') }}
    group by 1, 2, 3
    union all
    select 'rents', area_id, area_name_en, count(*)
    from {{ source('bronze', 'dld_rent_contracts') }}
    group by 1, 2, 3
)
select p.source, p.area_id, p.area_name_en as published_name, s.area_name_en as seed_name, p.lines
from published as p
left join {{ ref('seed_area') }} as s
    on s.area_id = nullif(p.area_id, '')::integer
where nullif(p.area_id, '') is not null
    and s.area_name_en is distinct from nullif(trim(p.area_name_en), '')
    and regexp_replace(s.area_name_en, ' \([^)]*\)$', '') is distinct from nullif(trim(p.area_name_en), '')
