{{
    config(
        indexes=[
            {'columns': ['transaction_id'], 'unique': true},
            {'columns': ['txn_date']},
            {'columns': ['area_key']},
            {'columns': ['is_market_sale', 'txn_date']},
        ]
    )
}}

-- One row per DLD transaction line: all 1.79M lines of every group (Sales, Gifts,
-- Mortgages), with keys to the star-schema dimensions and every silver quality flag.
-- Nothing is filtered: int_market_sales and int_mortgages partition stg_transactions
-- exactly (recon_transactions_partition), so their union is the whole register, and
-- recon_gold_transactions_vs_silver checks rows and AED against silver.
--
-- AED: `actual_worth_aed` is the value as registered. A portfolio deal repeats its total
-- on every unit line (C16), so SUM(actual_worth_aed) overstates value. **Sum
-- `aed_counted_once`** (the deal value on the lead line, 0 on the repeats): it is safe
-- to add up across any slice.
--
-- Columns that only exist on one side are filled for the other: price-quality flags
-- (C4-C6) are false for mortgages (no price is claimed), mortgage columns are false/NULL
-- for transfers.

with transfers as (

    select
        transaction_id,
        trans_group,
        procedure_id,
        procedure_name,
        procedure_category,
        is_market_sale,
        is_clean_market_sale,
        false as is_new_mortgage,
        false as is_portfolio_mortgage,
        false as amount_is_loan,
        is_lease_to_own,
        txn_date,
        is_date_invalid,
        is_pre_2004,
        property_type,
        property_sub_type,
        property_usage,
        is_residential,
        reg_type,
        is_offplan,
        area_id,
        building_name,
        project_number,
        has_project,
        nearest_metro,
        rooms_en,
        bedrooms,
        room_class,
        is_penthouse,
        is_commercial_unit,
        has_parking,
        area_sqm,
        actual_worth_aed,
        actual_worth_once_aed,
        price_per_sqm_aed,
        null::numeric as mortgage_amount_aed,
        null::numeric as mortgage_amount_once_aed,
        null::numeric as portfolio_mortgage_value_once_aed,
        is_price_below_floor,
        is_ppsqm_outlier,
        is_price_invalid,
        is_area_invalid,
        is_ppsqm_mismatch,
        is_repeated_deal_value,
        deal_group_id,
        deal_group_lines,
        is_deal_group_lead,
        is_similar_size_batch,
        batch_group_id
    from {{ ref('int_market_sales') }}

),

mortgages as (

    select
        transaction_id,
        trans_group,
        procedure_id,
        procedure_name,
        procedure_category,
        false as is_market_sale,
        false as is_clean_market_sale,
        is_new_mortgage,
        is_portfolio_mortgage,
        amount_is_loan,
        is_lease_to_own,
        txn_date,
        is_date_invalid,
        is_pre_2004,
        property_type,
        property_sub_type,
        property_usage,
        is_residential,
        reg_type,
        is_offplan,
        area_id,
        building_name,
        project_number,
        has_project,
        null::text as nearest_metro,
        rooms_en,
        bedrooms,
        room_class,
        false as is_penthouse,
        false as is_commercial_unit,
        null::boolean as has_parking,
        area_sqm,
        actual_worth_aed,
        actual_worth_once_aed,
        null::numeric as price_per_sqm_aed,
        mortgage_amount_aed,
        mortgage_amount_once_aed,
        portfolio_mortgage_value_once_aed,
        false as is_price_below_floor,
        false as is_ppsqm_outlier,
        false as is_price_invalid,
        false as is_area_invalid,
        false as is_ppsqm_mismatch,
        is_repeated_deal_value,
        deal_group_id,
        deal_group_lines,
        is_deal_group_lead,
        is_similar_size_batch,
        batch_group_id
    from {{ ref('int_mortgages') }}

),

lines as (

    select * from transfers
    union all
    select * from mortgages

)

select
    l.transaction_id,
    l.txn_date,
    coalesce(l.area_id, -1) as area_key,
    coalesce(pt.property_type_key, 999) as property_type_key,
    pm.procedure_key,
    coalesce(l.project_number, -1) as project_key,

    l.trans_group,
    l.procedure_name,
    l.procedure_category,
    l.is_market_sale,
    l.is_clean_market_sale,
    -- A market sale excluded from price statistics by a quality flag (C4-C6, C16, C18).
    l.is_market_sale and not l.is_clean_market_sale as has_quality_flag,
    l.is_new_mortgage,
    l.is_portfolio_mortgage,
    l.amount_is_loan,
    l.is_lease_to_own,
    l.reg_type,
    l.is_offplan,

    l.property_type,
    l.property_sub_type,
    l.property_usage,
    l.is_residential,
    l.building_name,
    l.has_project,
    l.nearest_metro,
    l.rooms_en,
    l.bedrooms,
    l.room_class,
    l.is_penthouse,
    l.is_commercial_unit,
    l.has_parking,

    -- Units: sq m and AED (docs/01 §7).
    l.area_sqm,
    l.actual_worth_aed::numeric(18, 2) as actual_worth_aed,
    l.actual_worth_once_aed::numeric(18, 2) as aed_counted_once,
    round(l.price_per_sqm_aed, 2)::numeric(18, 2) as price_per_sqm_aed,
    l.mortgage_amount_aed::numeric(18, 2) as mortgage_amount_aed,
    l.mortgage_amount_once_aed::numeric(18, 2) as mortgage_amount_once_aed,
    l.portfolio_mortgage_value_once_aed::numeric(18, 2) as portfolio_mortgage_value_once_aed,

    l.deal_group_id,
    l.deal_group_lines,
    l.is_deal_group_lead,
    l.batch_group_id,

    l.is_date_invalid,
    l.is_pre_2004,
    l.is_price_below_floor,
    l.is_ppsqm_outlier,
    l.is_price_invalid,
    l.is_area_invalid,
    l.is_ppsqm_mismatch,
    l.is_repeated_deal_value,
    l.is_similar_size_batch,

    -- Purchase mortgages (int_purchase_mortgage_pairs): a new mortgage and a ready sale of
    -- the same unit on the same day. The sale line carries has_purchase_mortgage (the
    -- numerator of the purchase-mortgage share of ready sales, docs/01 §4); the mortgage
    -- line carries is_purchase_mortgage and the observed loan-to-value.
    pm_m.mortgage_transaction_id is not null as is_purchase_mortgage,
    pm_s.sale_transaction_id is not null as has_purchase_mortgage,
    pm_m.purchase_ltv,

    -- Area-weighted price population (Σ AED / Σ sq m): the area must be plausible for the
    -- property class (macro class_area_cap: apartment 1,000 sq m, villa 3,000, office /
    -- retail 5,000, other 10,000). Doesn't change is_clean_market_sale (the median
    -- population); it only keeps plot-sized areas out of area-weighted sums.
    coalesce(pt.property_class_id, 99) as property_class_id,
    coalesce(l.area_sqm > {{ class_area_cap('coalesce(pt.property_class_id, 99)') }}, false)
        as is_area_above_class_cap,

    -- Dated from dim_date_start to the data snapshot date: the rows the aggregates and
    -- rpt.transactions carry. Outside: 1900-2003 registrations (C18 is_pre_2004) and the
    -- 4 Hijri-dated rows (no txn_date). The snapshot is the latest txn_date, so no valid
    -- transaction falls after it.
    coalesce(
        l.txn_date between date '{{ var("dim_date_start") }}' and snap.data_snapshot_date,
        false
    ) as is_in_report_scope
from lines as l
cross join {{ ref('int_data_snapshot') }} as snap
left join {{ ref('int_property_type_lookup') }} as pt
    on pt.source = 'transactions'
    and pt.property_usage_join = coalesce(l.property_usage, '')
    and pt.property_type_join = coalesce(l.property_type, '')
    and pt.property_sub_type_join = coalesce(l.property_sub_type, '')
left join {{ ref('seed_procedure_map') }} as pm
    on pm.trans_group = l.trans_group
    and pm.procedure_id = l.procedure_id
left join {{ ref('int_purchase_mortgage_pairs') }} as pm_m
    on pm_m.mortgage_transaction_id = l.transaction_id
left join {{ ref('int_purchase_mortgage_pairs') }} as pm_s
    on pm_s.sale_transaction_id = l.transaction_id
