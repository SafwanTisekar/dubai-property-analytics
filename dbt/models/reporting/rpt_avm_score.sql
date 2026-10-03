{{ config(alias='avm_score', tags=['post_ml']) }}

-- AVM valuations (docs/05 §1) for Power BI: one row per clean residential market sale the
-- champion model valued OUT OF SAMPLE (validation 2024, test 2025+; ~424k rows). The
-- training-period rows (2011-2023) stay in ml.avm_score: their gaps are in-sample, so they
-- would flatter the actual-vs-AVM chart, and they would double the model (decision, Phase 5).
-- The headline accuracy cards read rpt.avm_performance, which is unchanged.
-- "Gap Pct" = (price - AVM value) / AVM value: positive = sold above the AVM.
--
-- "Review Flag": |gap| > 25%. A statistical anomaly for a collateral review, NOT an
-- accusation of mispricing: the register doesn't record floor, view, condition or the
-- circumstances of a sale. "Transaction ID" is published only on flagged rows (look-up).
--
-- Left out to keep the import small (Phase 5 size budget): the comparable-sales value and
-- AVM value per sq m (~490k / 40k distinct values; the baseline comparison lives in
-- rpt.avm_performance) and the model name / version (one value; filtered below).
select
    s.txn_date as "Date",
    s.area_key as "Area Key",
    s.property_type_key as "Property Type Key",
    coalesce(t.project_key, -1) as "Project Key",
    s.bedrooms as "Bedrooms",
    {{ rpt_bedrooms_key('s.bedrooms') }} as "Bedrooms Key",
    s.is_offplan as "Is Off-Plan",
    {{ rpt_ready_offplan('s.is_offplan') }} as "Ready / Off-Plan",
    round(s.area_sqm, 2) as "Area Sq M",
    initcap(s.model_set) as "Model Set",
    {{ rpt_aed('s.actual_price_aed') }} as "Price AED",
    {{ rpt_aed('s.predicted_value_aed') }} as "AVM Value AED",
    round(s.abs_pct_error, 4) as "Absolute Error Pct",
    round(s.gap_pct, 4) as "Gap Pct",
    case
        when s.is_review then 'Review: statistical anomaly'
        else 'Within range'
    end as "Review Flag",
    case when s.is_review then s.transaction_id end as "Transaction ID"
from {{ source('ml', 'avm_score') }} as s
left join {{ ref('fct_transaction') }} as t on t.transaction_id = s.transaction_id
where s.model_version = '{{ var("avm_model_version") }}'
    and s.model_set <> 'train'
