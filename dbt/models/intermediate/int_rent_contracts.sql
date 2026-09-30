-- One row per Ejari contract line (~10.5M), with the rent rules that need every line of a
-- contract at once (docs/04 §2: C11-C14, C18, C20-C22). Nothing is filtered out;
-- `is_market_rent` picks the population for market rents and yields.
--
-- C11 (decided: option 1, phase1_findings §3). Every multi-line contract repeats the
-- contract's full amount on each line, so a naive sum over lines is 5.24x the truth.
--   * `line_count` counts the lines (no_of_prop is wrong on 5,629 contracts).
--   * `annual_rent_alloc_aed` = contract annual rent / line_count, so any SUM over lines
--     counts each contract once. Always sum this column, never annual_amount_aed.
--   * Market rent and yields use single-line contracts only (`is_market_rent` requires
--     not is_multi_unit): a bulk lease of a whole floor is not a like-for-like unit rent,
--     and an equal split is not a unit's rent either.
--
-- Rent detail never goes to Power BI (CLAUDE.md); gold will aggregate it.

with lines as (

    select
        s.*,
        count(*) over contract as line_count,
        -- Phase 1 found every line of a contract carries the same amount; if a future
        -- snapshot breaks that, the allocation below would be ambiguous, so flag it.
        min(s.annual_amount_aed) over contract is distinct from max(s.annual_amount_aed) over contract
            as is_amount_inconsistent,
        s.end_date - s.start_date + 1 as contract_days,
        -- Conformed property class for the C21 area cap. Ejari maps on property type alone
        -- (seed_property_type_map rows for rents have no sub-type), exactly as
        -- int_property_type_lookup does; fct_rent_contract tests that the two agree.
        coalesce(pc.property_class_id, 99) as property_class_id,
        snap.data_snapshot_date
    from {{ ref('stg_rent_contracts') }} as s
    left join {{ ref('seed_property_type_map') }} as tm
        on tm.source = 'rents'
        and tm.property_type = s.property_type
        and tm.property_sub_type is null
    left join {{ ref('seed_property_class') }} as pc
        on pc.property_class = tm.property_class
    cross join {{ ref('int_data_snapshot') }} as snap
    window contract as (partition by s.contract_id)

),

measured as (

    select
        *,
        line_count > 1 as is_multi_unit,

        -- C12: annual_amount is the annualised contract value. If it were ever missing,
        -- annualise contract_amount by the contract length.
        coalesce(
            annual_amount_aed,
            contract_amount_aed * 365.0 / nullif(contract_days, 0)
        ) as annual_rent_contract_aed,
        coalesce(
            annual_amount_aed,
            contract_amount_aed * 365.0 / nullif(contract_days, 0)
        ) / line_count as annual_rent_alloc_aed,

        -- C18: dates. Contracts can be registered ahead of their start, so only a start
        -- more than a year after the extract is invalid (104 lines, up to year 2205).
        (
            start_date is null
            or start_date > snapshot_date + {{ var('rent_max_days_after_snapshot') }}
        ) as is_date_invalid,
        coalesce(start_date < date '{{ var("analysis_start_date") }}', false) as is_pre_2004,
        -- C18: a valid start after the data snapshot date (the latest transaction date).
        -- Registered ahead of time; not yet a market rent, and outside the report scope.
        coalesce(
            start_date > data_snapshot_date
            and start_date <= snapshot_date + {{ var('rent_max_days_after_snapshot') }},
            false
        ) as is_start_after_snapshot,
        -- End dates reach year 5013. More than 10 years, or ending before the start, is
        -- a keying error for a residential or commercial lease.
        (
            end_date is null
            or end_date < start_date
            or contract_days > {{ var('rent_max_contract_days') }}
        ) as is_end_date_implausible,

        -- C20: not market rents. Virtual units are flexi-desk / trade-licence addresses;
        -- labour camps are bed-space accommodation (phase1_findings §3).
        (
            coalesce(bus_property_type = 'Virtual Unit', false)
            or coalesce(property_type = 'Labor Camps', false)
            or coalesce(property_sub_type in ('Room in labor Camp', 'Labor Camp'), false)
        ) as is_non_market_property_type,

        -- C21: blank, 0 and 1 sq m are placeholders (1.55M lines): no area, no rent/sq m.
        -- Above the cap for the property class (apartment 1,000 sq m, villa 3,000, office /
        -- retail 5,000, other 10,000; macro class_area_cap) the area is a whole community,
        -- plot or building (e.g. 378,236 sq m on many 3-bed villas, one at 375M sq m). Such
        -- lines were 0.3% of comparable lines but 89% of their summed area. The rent is
        -- kept; the line gets no area and no rent per sq m.
        case
            when actual_area_sqm > {{ var('rent_area_placeholder_sqm') }}
                and actual_area_sqm <= {{ class_area_cap('property_class_id') }}
                then actual_area_sqm
        end as area_sqm,
        coalesce(actual_area_sqm <= {{ var('rent_area_placeholder_sqm') }}, true)
            as is_area_placeholder,
        coalesce(actual_area_sqm > {{ class_area_cap('property_class_id') }}, false)
            as is_area_implausible
    from lines

),

priced as materialized (

    select
        *,
        -- Per sq m only for single-line contracts with a real area: for a multi-unit
        -- contract an equal split divided by one unit's area is not that unit's rent.
        case
            when not is_multi_unit and area_sqm is not null
                then annual_rent_contract_aed / area_sqm
        end as rent_per_sqm_aed,
        -- C14 (floor)
        coalesce(annual_rent_alloc_aed < {{ var('rent_floor_aed') }}, true) as is_rent_below_floor
    from measured

),

-- C14 (bands): P0.5-P99.5 by area x Ejari sub-type, fitted on single-line market-type
-- contracts above the floor. Rent per sq m where the area is real; annual rent otherwise.
-- Segments under the min-n rule fall back to the sub-type's Dubai-wide band.
band_population as (

    select area_id, property_sub_type, rent_per_sqm_aed, annual_rent_alloc_aed
    from priced
    where not is_multi_unit
        and not is_non_market_property_type
        and not is_rent_below_floor
        and not is_date_invalid

),

area_bands as (

    select
        area_id,
        property_sub_type,
        count(rent_per_sqm_aed) as sqm_n,
        count(*) as annual_n,
        percentile_cont(array[{{ var('band_low') }}, {{ var('band_high') }}])
            within group (order by rent_per_sqm_aed) as sqm_band,
        percentile_cont(array[{{ var('band_low') }}, {{ var('band_high') }}])
            within group (order by annual_rent_alloc_aed) as annual_band
    from band_population
    group by 1, 2

),

subtype_bands as (

    select
        property_sub_type,
        count(rent_per_sqm_aed) as sqm_n,
        count(*) as annual_n,
        percentile_cont(array[{{ var('band_low') }}, {{ var('band_high') }}])
            within group (order by rent_per_sqm_aed) as sqm_band,
        percentile_cont(array[{{ var('band_low') }}, {{ var('band_high') }}])
            within group (order by annual_rent_alloc_aed) as annual_band
    from band_population
    group by 1

),

banded as (

    select
        p.*,
        case
            when ab.sqm_n >= {{ var('min_n') }} then ab.sqm_band
            when sb.sqm_n >= {{ var('min_n') }} then sb.sqm_band
        end as sqm_band,
        case
            when ab.annual_n >= {{ var('min_n') }} then ab.annual_band
            when sb.annual_n >= {{ var('min_n') }} then sb.annual_band
        end as annual_band,
        case
            when p.rent_per_sqm_aed is not null and ab.sqm_n >= {{ var('min_n') }} then 'area_x_subtype'
            when p.rent_per_sqm_aed is not null and sb.sqm_n >= {{ var('min_n') }} then 'subtype'
            when p.rent_per_sqm_aed is null and ab.annual_n >= {{ var('min_n') }} then 'area_x_subtype'
            when p.rent_per_sqm_aed is null and sb.annual_n >= {{ var('min_n') }} then 'subtype'
        end as rent_band_level
    from priced as p
    left join area_bands as ab
        on ab.area_id = p.area_id
        and ab.property_sub_type = p.property_sub_type
    left join subtype_bands as sb
        on sb.property_sub_type = p.property_sub_type

),

flagged as (

    select
        *,
        is_rent_below_floor
            or coalesce(
                case
                    when rent_per_sqm_aed is not null
                        then rent_per_sqm_aed not between sqm_band[1] and sqm_band[2]
                    else annual_rent_alloc_aed not between annual_band[1] and annual_band[2]
                end,
                false
            ) as is_rent_outlier
    from banded

)

select
    contract_id,
    line_number,
    line_count,
    is_multi_unit,
    no_of_prop_source,
    contract_reg_type,
    is_new,

    start_date,
    end_date,
    start_date_raw,
    end_date_raw,
    contract_days,
    is_date_invalid,
    is_pre_2004,
    is_start_after_snapshot,
    is_end_date_implausible,

    contract_amount_aed,
    annual_amount_aed,
    is_amount_inconsistent,
    annual_rent_contract_aed,
    annual_rent_alloc_aed,

    bus_property_type,
    property_type,
    property_sub_type,
    property_usage,
    is_residential,
    is_free_hold,
    is_non_market_property_type,
    bedrooms,
    room_class,

    property_class_id,
    area_id,
    area_name,
    zone,
    project_number,
    project_name,
    master_project,
    nearest_landmark,
    nearest_metro,
    nearest_mall,

    actual_area_sqm,
    area_sqm,
    is_area_placeholder,
    is_area_implausible,
    rent_per_sqm_aed,

    is_rent_below_floor,
    rent_band_level,
    case when rent_per_sqm_aed is not null then sqm_band[1] end as rent_per_sqm_band_low,
    case when rent_per_sqm_aed is not null then sqm_band[2] end as rent_per_sqm_band_high,
    case when rent_per_sqm_aed is null then annual_band[1] end as annual_rent_band_low,
    case when rent_per_sqm_aed is null then annual_band[2] end as annual_rent_band_high,
    is_rent_outlier,

    tenant_type,

    -- Market rent (C13 + C11 + C14 + C20): new contracts only (renewals lag the market),
    -- single-line, a market property type, inside the band, with usable dates.
    is_new
        and not is_multi_unit
        and not is_non_market_property_type
        and not is_rent_outlier
        and not is_date_invalid
        and not is_pre_2004
        and not is_start_after_snapshot
        and not is_end_date_implausible
        as is_market_rent,

    snapshot_date,
    source_file
from flagged
