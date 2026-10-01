{{ config(alias='dim_area') }}

-- Areas (DLD communities) with zone and centroid for the bubble map. Centroids are from
-- OpenStreetMap (seed_area.centroid_source, reports/area_centroids.md); NULL where an area
-- wasn't located, so it has no bubble. Map credit: rpt.report_info "Map Attribution".
select
    area_key as "Area Key",
    area_name as "Area",
    zone as "Zone",
    latitude as "Latitude",
    longitude as "Longitude"
from {{ ref('dim_area') }}
