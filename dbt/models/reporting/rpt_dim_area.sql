{{ config(alias='dim_area') }}

-- Areas (DLD communities) with zone and centroid (NULL until Phase 5).
select
    area_key as "Area Key",
    area_name as "Area",
    zone as "Zone",
    latitude as "Latitude",
    longitude as "Longitude"
from {{ ref('dim_area') }}
