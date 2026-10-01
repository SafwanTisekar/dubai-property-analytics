{{ config(alias='avm_score', tags=['post_ml']) }}

-- AVM valuations (docs/05 §1): one row per clean residential market sale the champion
-- model values. "Gap %" = (price - AVM value) / AVM value: positive = sold above the AVM.
--
-- "Review Flag": |gap| > 25% on an out-of-sample valuation (validation 2024, test 2025+).
-- These are statistical anomalies for a collateral review, NOT accusations of mispricing:
-- the register doesn't record floor, view, condition or the circumstances of a sale.
-- Training-period rows (2011-2023) are never flagged (blank): the model has fitted those
-- sales, so their gaps understate how unusual the price was.
--
-- "Transaction ID" is published only on flagged rows (for look-up); the ids of the other
-- ~0.9M rows stay in ml / gold to keep the Power BI model small (docs/06 §1).
select
    s.txn_date as "Date",
    s.area_key as "Area Key",
    s.property_type_key as "Property Type Key",
    s.bedrooms as "Bedrooms",
    s.is_offplan as "Is Off-Plan",
    round(s.area_sqm, 2) as "Area Sq M",
    initcap(s.model_set) as "Model Set",
    s.model_set <> 'train' as "Is Out of Sample",
    {{ rpt_aed('s.actual_price_aed') }} as "Price AED",
    {{ rpt_aed('s.predicted_value_aed') }} as "AVM Value AED",
    {{ rpt_aed('s.predicted_ppsqm_aed') }} as "AVM Value per Sq M AED",
    {{ rpt_aed('s.comps_value_aed') }} as "Comparable Sales Value AED",
    round(s.abs_pct_error, 4) as "Absolute Error Pct",
    round(s.gap_pct, 4) as "Gap Pct",
    case
        when s.is_review then 'Review: statistical anomaly'
        when s.is_review is not null then 'Within range'
    end as "Review Flag",
    case when s.is_review then s.transaction_id end as "Transaction ID",
    s.model as "Model",
    s.model_version as "Model Version"
from {{ source('ml', 'avm_score') }} as s
where s.model_version = '{{ var("avm_model_version") }}'
