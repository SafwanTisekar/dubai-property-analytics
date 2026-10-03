-- One row per DLD transaction line: typed, de-duplicated across snapshots and decoded.
-- Rules applied here (docs/04 §2): C1 de-duplication and typing, C2 procedure map,
-- C7 rooms map, C8 area seed, C9 has_project, C18 date flags, C19 property_usage fix.
-- No row is filtered except C1 duplicates; everything else is a column or a flag.
-- Arabic (_ar) columns are dropped here (docs/01 §7).

with source as (

    select * from {{ source('bronze', 'dld_transactions') }}

),

-- C1: the same transaction_id can arrive in several snapshots. Keep the latest version.
-- transaction_id is unique within a snapshot (Phase 1), so this also absorbs corrections
-- DLD makes between extracts, not only byte-identical repeats (_row_hash).
deduplicated as (

    select
        *,
        row_number() over (
            partition by transaction_id
            order by _snapshot_date desc, _ingested_at desc, _row_hash
        ) as snapshot_rank
    from source

),

typed as (

    select
        transaction_id,
        -- transaction_id = <group>-<procedure>-<year>-<seq>. The year is when the
        -- application was opened and the seq is DLD's running number within that year,
        -- which is what C16 uses to spot lines registered in one batch.
        split_part(transaction_id, '-', 3) as id_year,
        nullif(split_part(transaction_id, '-', 4), '')::integer as id_seq,

        {{ to_num('trans_group_id', 'smallint') }} as trans_group_id,
        {{ clean_text('trans_group_en') }} as trans_group,
        {{ to_num('procedure_id', 'integer') }} as procedure_id,
        {{ clean_text('procedure_name_en') }} as procedure_name,

        {{ clean_text('instance_date') }} as instance_date_raw,
        {{ safe_iso_date('instance_date') }} as parsed_date,

        {{ clean_text('property_type_en') }} as property_type,
        {{ clean_text('property_sub_type_en') }} as property_sub_type,
        -- C19: one category has its EN and AR labels swapped (6,322 rows, phase1_findings §5).
        case
            when trim(property_usage_en) = 'أخرى' then 'Other'
            else {{ clean_text('property_usage_en') }}
        end as property_usage,
        {{ to_num('reg_type_id', 'smallint') }} as reg_type_id,
        {{ clean_text('reg_type_en') }} as reg_type,

        {{ to_num('area_id', 'integer') }} as area_id,
        {{ clean_text('area_name_en') }} as area_name_source,
        {{ clean_text('building_name_en') }} as building_name,
        {{ to_int('project_number') }} as project_number,
        {{ clean_text('project_name_en') }} as project_name,
        {{ clean_text('master_project_en') }} as master_project,
        {{ clean_text('nearest_landmark_en') }} as nearest_landmark,
        {{ clean_text('nearest_metro_en') }} as nearest_metro,
        {{ clean_text('nearest_mall_en') }} as nearest_mall,

        {{ clean_text('rooms_en') }} as rooms_en,
        {{ to_bool01('has_parking') }} as has_parking,

        -- Units: sq m and AED, as published (docs/01 §7). No sq ft anywhere.
        {{ to_num('procedure_area') }} as area_sqm,
        {{ to_num('actual_worth') }} as actual_worth_aed,
        {{ to_num('meter_sale_price') }} as meter_sale_price_aed,
        {{ to_num('rent_value') }} as rent_value_aed,
        {{ to_num('meter_rent_price') }} as meter_rent_price_aed,

        {{ to_num('no_of_parties_role_1', 'integer') }} as no_of_parties_role_1,
        {{ to_num('no_of_parties_role_2', 'integer') }} as no_of_parties_role_2,
        {{ to_num('no_of_parties_role_3', 'integer') }} as no_of_parties_role_3,

        {{ clean_text('load_timestamp') }}::timestamptz as dld_extracted_at,
        _snapshot_date as snapshot_date,
        _source_file as source_file,
        _row_hash as row_hash
    from deduplicated
    where snapshot_rank = 1

)

select
    t.transaction_id,
    t.id_year,
    t.id_seq,
    t.trans_group_id,
    t.trans_group,
    t.procedure_id,
    t.procedure_name,

    -- C2: category and flags from the seed, keyed on (trans_group, procedure_id) because
    -- six lease-to-own codes exist in both Sales and Mortgages (phase1_findings §1).
    pm.procedure_category,
    coalesce(pm.is_market_sale, false) as is_market_sale,
    coalesce(pm.is_lease_to_own, false) as is_lease_to_own,
    coalesce(pm.is_new_mortgage, false) as is_new_mortgage,
    coalesce(pm.is_portfolio_mortgage, false) as is_portfolio_mortgage,
    coalesce(pm.amount_is_loan, false) as amount_is_loan,

    -- C18: dates. Four rows carry Hijri years (1416-1422 AH); they parse as valid ISO
    -- dates in the 15th century, so the year check is what catches them. They get no
    -- txn_date and a flag rather than a conversion (phase1_findings §4).
    case
        when t.parsed_date >= date '1900-01-01' and t.parsed_date <= t.snapshot_date
            then t.parsed_date
    end as txn_date,
    t.instance_date_raw,
    (
        t.parsed_date is null
        or t.parsed_date < date '1900-01-01'
        or t.parsed_date > t.snapshot_date
    ) as is_date_invalid,
    coalesce(
        t.parsed_date >= date '1900-01-01'
        and t.parsed_date < date '{{ var("analysis_start_date") }}',
        false
    ) as is_pre_2004,

    t.property_type,
    t.property_sub_type,
    t.property_usage,
    t.property_usage = 'Residential' as is_residential,
    t.reg_type_id,
    t.reg_type,
    t.reg_type = 'Off-Plan Properties' as is_offplan,

    -- C8: area from the seed (canonical name + zone); the source name is kept so name
    -- drift between snapshots can be tested.
    t.area_id,
    coalesce(a.area_name_en, t.area_name_source) as area_name,
    t.area_name_source,
    a.zone,
    t.building_name,
    t.project_number,
    t.project_name,
    t.master_project,
    -- C9: 26% of rows have no project. Kept as NULL here, labelled "Unknown" in gold.
    t.project_number is not null as has_project,
    t.nearest_landmark,
    t.nearest_metro,
    t.nearest_mall,

    -- C7: rooms label -> bedrooms (Studio = 0) and unit flags.
    t.rooms_en,
    r.bedrooms,
    r.room_class,
    coalesce(r.is_penthouse, false) as is_penthouse,
    coalesce(r.is_commercial_unit, false) as is_commercial_unit,
    t.has_parking,

    t.area_sqm,
    t.actual_worth_aed,
    t.meter_sale_price_aed,
    t.rent_value_aed,
    t.meter_rent_price_aed,
    t.no_of_parties_role_1,
    t.no_of_parties_role_2,
    t.no_of_parties_role_3,

    t.dld_extracted_at,
    t.snapshot_date,
    t.source_file,
    t.row_hash
from typed as t
left join {{ ref('seed_procedure_map') }} as pm
    on pm.trans_group = t.trans_group
    and pm.procedure_id = t.procedure_id
left join {{ ref('seed_area') }} as a
    on a.area_id = t.area_id
left join {{ ref('seed_rooms_map') }} as r
    on r.rooms_en = t.rooms_en
