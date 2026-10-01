-- One row per DLD area (all 265 area IDs in seed_area, every one zoned; docs/04 §6) plus an
-- Unknown member (-1) for the 3 rent lines with no area. area_key = DLD area_id, so the
-- key is readable and stable across rebuilds. Centroids (for the Power BI bubble map,
-- docs/06 §4) come from OpenStreetMap via seed_area; NULL where an area wasn't located.

select
    area_id as area_key,
    area_id,
    area_name_en as area_name,
    zone,
    latitude,
    longitude,
    centroid_source
from {{ ref('seed_area') }}

union all

select -1, null, 'Unknown', 'Unknown', null, null, null
