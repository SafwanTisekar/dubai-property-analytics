-- One row per Ejari contract line: typed, de-duplicated across snapshots and decoded.
-- Rules applied here (docs/04 §2): C1 de-duplication and typing, C8 area seed, C22 rent
-- sub-type -> bedrooms. Contract-level logic (C11-C14, C18, C20, C21) needs every line of a
-- contract at once, so it lives in int_rent_contracts. Arabic (_ar) columns are dropped.
--
-- This is a view over ~10.5M rows: only int_rent_contracts should select from it.

with source as (

    select * from {{ source('bronze', 'dld_rent_contracts') }}

),

-- C1: a contract line (contract_id, line_number) can arrive in several snapshots. Keep
-- the latest version.
deduplicated as (

    select
        *,
        row_number() over (
            partition by contract_id, line_number
            order by _snapshot_date desc, _ingested_at desc, _row_hash
        ) as snapshot_rank
    from source

)

select
    d.contract_id,
    {{ to_num('d.line_number', 'integer') }} as line_number,
    -- no_of_prop disagrees with the real line count on 5,629 contracts (phase1_findings §3),
    -- so int_rent_contracts counts lines instead. Kept for reference only.
    {{ to_num('d.no_of_prop', 'integer') }} as no_of_prop_source,

    {{ clean_text('d.contract_reg_type_en') }} as contract_reg_type,
    trim(d.contract_reg_type_en) = 'New' as is_new,

    {{ clean_text('d.contract_start_date') }} as start_date_raw,
    {{ clean_text('d.contract_end_date') }} as end_date_raw,
    {{ safe_iso_date('d.contract_start_date') }} as start_date,
    {{ safe_iso_date('d.contract_end_date') }} as end_date,

    {{ to_num('d.contract_amount') }} as contract_amount_aed,
    {{ to_num('d.annual_amount') }} as annual_amount_aed,

    {{ clean_text('d.ejari_bus_property_type_en') }} as bus_property_type,
    {{ clean_text('d.ejari_property_type_en') }} as property_type,
    {{ clean_text('d.ejari_property_sub_type_en') }} as property_sub_type,
    {{ clean_text('d.property_usage_en') }} as property_usage,
    trim(d.property_usage_en) = 'Residential' as is_residential,
    {{ to_bool01('d.is_free_hold') }} as is_free_hold,

    {{ to_num('d.area_id', 'integer') }} as area_id,
    coalesce(a.area_name_en, {{ clean_text('d.area_name_en') }}) as area_name,
    {{ clean_text('d.area_name_en') }} as area_name_source,
    a.zone,
    {{ to_int('d.project_number') }} as project_number,
    {{ clean_text('d.project_name_en') }} as project_name,
    {{ clean_text('d.master_project_en') }} as master_project,
    {{ clean_text('d.nearest_landmark_en') }} as nearest_landmark,
    {{ clean_text('d.nearest_metro_en') }} as nearest_metro,
    {{ clean_text('d.nearest_mall_en') }} as nearest_mall,

    -- Raw per-line area in sq m. Blank on 12.6% of lines, 0 or 1 on many more: C21.
    {{ to_num('d.actual_area') }} as actual_area_sqm,

    -- C22: Ejari sub-type label -> bedrooms (Studio = 0); NULL for non-residential layouts.
    rs.bedrooms,
    rs.room_class,

    {{ clean_text('d.tenant_type_en') }} as tenant_type,

    {{ clean_text('d.load_timestamp') }}::timestamptz as dld_extracted_at,
    d._snapshot_date as snapshot_date,
    d._source_file as source_file,
    d._row_hash as row_hash
from deduplicated as d
left join {{ ref('seed_area') }} as a
    on a.area_id = {{ to_num('d.area_id', 'integer') }}
left join {{ ref('seed_rent_subtype_map') }} as rs
    on rs.ejari_property_sub_type_en = {{ clean_text('d.ejari_property_sub_type_en') }}
where d.snapshot_rank = 1
