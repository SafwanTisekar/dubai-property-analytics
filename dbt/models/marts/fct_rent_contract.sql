{{
    config(
        indexes=[
            {'columns': ['contract_id', 'line_number'], 'unique': true},
            {'columns': ['start_date']},
            {'columns': ['area_key']},
            {'columns': ['is_market_rent', 'start_date']},
        ]
    )
}}

-- One row per Ejari contract line (~10.5M), de-duplicated in silver (C1), with keys to the
-- shared dimensions. Never sent to Power BI in detail (CLAUDE.md): agg_rent_month is the
-- rent table the report imports.
--
-- AED: every line of a multi-unit contract repeats the whole contract amount (C11), so
-- **sum `annual_rent_alloc_aed` only** (contract annual rent / line count). It is kept
-- at full precision rather than numeric(18,2): rounding each share to fils would stop the
-- shares adding back to the contract amount, which the C11 tests check.
--
-- is_rent_comparable = a like-for-like unit rent (single line, market property type,
-- inside the C14 band, usable dates, started by the data snapshot date) whether new or
-- renewed; is_market_rent adds "new contract" (C13), the default market rent (CLAUDE.md).

select
    r.contract_id,
    r.line_number,
    r.start_date,
    r.end_date,
    coalesce(r.area_id, -1) as area_key,
    coalesce(pt.property_type_key, 999) as property_type_key,
    r.property_class_id,

    r.contract_reg_type,
    r.is_new,
    r.line_count,
    r.is_multi_unit,
    r.contract_days,

    r.bus_property_type,
    r.property_type,
    r.property_sub_type,
    r.property_usage,
    r.is_residential,
    r.is_free_hold,
    r.bedrooms,
    r.room_class,
    r.project_number,
    r.project_name,
    r.tenant_type,

    r.area_sqm,
    r.contract_amount_aed::numeric(18, 2) as contract_amount_aed,
    r.annual_rent_contract_aed::numeric(18, 2) as annual_rent_contract_aed,
    r.annual_rent_alloc_aed,
    round(r.rent_per_sqm_aed, 2)::numeric(18, 2) as rent_per_sqm_aed,

    r.is_date_invalid,
    r.is_pre_2004,
    r.is_start_after_snapshot,
    r.is_end_date_implausible,
    r.is_amount_inconsistent,
    r.is_non_market_property_type,
    r.is_area_placeholder,
    r.is_area_implausible,
    r.is_rent_below_floor,
    r.is_rent_outlier,

    not r.is_multi_unit
        and not r.is_non_market_property_type
        and not r.is_rent_outlier
        and not r.is_date_invalid
        and not r.is_pre_2004
        and not r.is_start_after_snapshot
        and not r.is_end_date_implausible
        as is_rent_comparable,
    r.is_market_rent,

    -- Starts from dim_date_start to the data snapshot date with a valid date: the lines
    -- agg_rent_month carries. Outside: C18 invalid starts (up to year 2205), starts after
    -- the snapshot (registered ahead) and the one pre-2004 line.
    (
        not r.is_date_invalid
        and not r.is_start_after_snapshot
        and r.start_date >= date '{{ var("dim_date_start") }}'
    ) as is_in_report_scope
from {{ ref('int_rent_contracts') }} as r
left join {{ ref('int_property_type_lookup') }} as pt
    on pt.source = 'rents'
    and pt.property_usage_join = coalesce(r.property_usage, '')
    and pt.property_type_join = coalesce(r.property_type, '')
    and pt.property_sub_type_join = coalesce(r.property_sub_type, '')
