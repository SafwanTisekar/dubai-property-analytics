{{ config(alias='report_info') }}

-- One row for the report header and footer: the data snapshot date (latest transaction
-- date, the end of the reporting scope), the min-n threshold and the attributions the
-- licences require: DLD data (CC BY 4.0, docs/01 §7) and the OpenStreetMap area centroids
-- behind the map (ODbL).
select
    (select max(date) from {{ ref('dim_date') }} where not is_after_snapshot) as "Data As Of",
    {{ var('min_n') }} as "Min N",
    'Dubai Land Department, CC BY 4.0' as "Source",
    'Area locations © OpenStreetMap contributors (ODbL)' as "Map Attribution"
