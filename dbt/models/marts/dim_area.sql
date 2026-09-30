-- One row per DLD area (all 265 area IDs in seed_area, every one zoned; docs/04 §6) plus an
-- Unknown member (-1) for the 3 rent lines with no area. area_key = DLD area_id, so the
-- key is readable and stable across rebuilds. Centroids are NULL until Phase 5 fills them
-- in seed_area (for the bubble map, docs/06 §4).

select
    area_id as area_key,
    area_id,
    area_name_en as area_name,
    zone,
    latitude,
    longitude
from {{ ref('seed_area') }}

union all

select -1, null, 'Unknown', 'Unknown', null, null
