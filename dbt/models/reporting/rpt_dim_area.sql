{{ config(alias='dim_area') }}

-- Areas (DLD communities) with zone and centroid for the bubble map. Centroids are from
-- OpenStreetMap (seed_area.centroid_source, reports/area_centroids.md); NULL where an area
-- wasn't located, so it has no bubble. Map credit: rpt.report_info "Map Attribution".
select
    a.area_key as "Area Key",
    a.area_name as "Area",
    a.zone as "Zone",
    z.zone_short as "Zone Short",
    a.latitude as "Latitude",
    a.longitude as "Longitude"
from {{ ref('dim_area') }} as a
left join {{ ref('seed_zone_label') }} as z on z.zone = a.zone
