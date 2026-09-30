-- Ownership transfers: every Sales- and Gifts-group line, with the quality flags that
-- decide what feeds prices, indices, yields and the AVM (docs/04 §2, C3-C6, C16-C18).
--
-- Nothing is filtered out. `is_market_sale` (from seed_procedure_map) picks arm's-length
-- sales; `is_clean_market_sale` additionally drops every flagged row and is the population
-- for price statistics and the AVM. Gifts, development transfers and the Sales leg of
-- lease-to-own deals stay here for volume counts only (C3, C17).
-- Mortgage-group lines are in int_mortgages; together the two models hold every line of
-- stg_transactions exactly once (tested).

with transfers as (

    select
        t.*,
        g.is_repeated_deal_value,
        g.deal_group_id,
        g.deal_group_lines,
        g.is_deal_group_lead,
        g.actual_worth_once_aed,
        g.is_similar_size_batch,
        g.batch_group_id,
        g.batch_group_lines
    from {{ ref('stg_transactions') }} as t
    inner join {{ ref('int_transaction_deal_groups') }} as g
        on g.transaction_id = t.transaction_id
    where t.trans_group in ('Sales', 'Gifts')

),

measured as (

    select
        *,
        -- C6: recompute rather than trust meter_sale_price.
        actual_worth_aed / nullif(area_sqm, 0) as price_per_sqm_aed,

        -- C4 (floor): below AED 50k is a nominal or partial-share value, not a unit price.
        coalesce(actual_worth_aed < {{ var('price_floor_aed') }}, true) as is_price_below_floor,

        -- C5: plausible size by property type. Land and whole buildings vary too much for
        -- a range, so they only need a real area.
        case
            when area_sqm is null then true
            when property_type = 'Unit'
                then area_sqm not between {{ var('unit_area_min_sqm') }}
                    and {{ var('unit_area_max_sqm') }}
            when property_type = 'Villa'
                then area_sqm not between {{ var('unit_area_min_sqm') }}
                    and {{ var('villa_area_max_sqm') }}
            else area_sqm < {{ var('land_area_min_sqm') }}
        end as is_area_invalid

    from transfers

),

-- C4 (band): P0.5-P99.5 of price per sq m by area x property type, over clean market
-- sales only (a band fitted on gifts and AED 1 rows would be meaningless). Segments below
-- the min-n rule fall back to the property type's Dubai-wide band.
band_population as (

    select area_id, property_type, price_per_sqm_aed
    from measured
    where is_market_sale
        and not is_date_invalid
        and not is_pre_2004
        and not is_repeated_deal_value
        and not is_price_below_floor
        and not is_area_invalid

),

area_bands as (

    select
        area_id,
        property_type,
        count(*) as band_n,
        percentile_cont({{ var('band_low') }}) within group (order by price_per_sqm_aed) as band_low,
        percentile_cont({{ var('band_high') }}) within group (order by price_per_sqm_aed) as band_high
    from band_population
    group by 1, 2
    having count(*) >= {{ var('min_n') }}

),

type_bands as (

    select
        property_type,
        count(*) as band_n,
        percentile_cont({{ var('band_low') }}) within group (order by price_per_sqm_aed) as band_low,
        percentile_cont({{ var('band_high') }}) within group (order by price_per_sqm_aed) as band_high
    from band_population
    group by 1
    having count(*) >= {{ var('min_n') }}

),

flagged as (

    select
        m.*,
        case
            when ab.area_id is not null then 'area_x_type'
            when tb.property_type is not null then 'type'
        end as ppsqm_band_level,
        coalesce(ab.band_low, tb.band_low) as ppsqm_band_low,
        coalesce(ab.band_high, tb.band_high) as ppsqm_band_high
    from measured as m
    left join area_bands as ab
        on ab.area_id = m.area_id
        and ab.property_type = m.property_type
    left join type_bands as tb
        on tb.property_type = m.property_type

),

outliers as (

    select
        *,
        coalesce(
            price_per_sqm_aed not between ppsqm_band_low and ppsqm_band_high, false
        ) as is_ppsqm_outlier,
        -- C6: only testable where DLD published a non-zero meter_sale_price.
        coalesce(
            abs(price_per_sqm_aed - meter_sale_price_aed) / nullif(meter_sale_price_aed, 0)
                > {{ var('ppsqm_tolerance') }},
            false
        ) as is_ppsqm_mismatch
    from flagged

)

select
    transaction_id,
    trans_group,
    procedure_id,
    procedure_name,
    procedure_category,
    is_market_sale,
    is_lease_to_own,
    txn_date,
    instance_date_raw,
    is_date_invalid,
    is_pre_2004,

    property_type,
    property_sub_type,
    property_usage,
    is_residential,
    reg_type,
    is_offplan,
    area_id,
    area_name,
    zone,
    building_name,
    project_number,
    project_name,
    master_project,
    has_project,
    nearest_landmark,
    nearest_metro,
    nearest_mall,
    rooms_en,
    bedrooms,
    room_class,
    is_penthouse,
    is_commercial_unit,
    has_parking,

    area_sqm,
    actual_worth_aed,
    price_per_sqm_aed,
    meter_sale_price_aed,

    -- C4
    is_price_below_floor,
    ppsqm_band_level,
    ppsqm_band_low,
    ppsqm_band_high,
    is_ppsqm_outlier,
    is_price_below_floor or is_ppsqm_outlier as is_price_invalid,
    -- C5, C6
    is_area_invalid,
    is_ppsqm_mismatch,

    -- C16
    is_repeated_deal_value,
    deal_group_id,
    deal_group_lines,
    is_deal_group_lead,
    actual_worth_once_aed,
    is_similar_size_batch,
    batch_group_id,
    batch_group_lines,

    -- The population for prices, indices, yields and the AVM: an arm's-length sale with
    -- a valid date in scope and no quality flag. Similar-size batches stay in: identical
    -- units at identical prices are real prices (phase1_findings §2b).
    is_market_sale
        and not is_date_invalid
        and not is_pre_2004
        and not is_repeated_deal_value
        and not is_price_below_floor
        and not is_ppsqm_outlier
        and not is_area_invalid
        and not is_ppsqm_mismatch
        as is_clean_market_sale,

    snapshot_date,
    source_file
from outliers
