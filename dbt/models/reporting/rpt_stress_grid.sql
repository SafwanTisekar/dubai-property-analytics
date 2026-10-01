{{ config(alias='stress_grid', tags=['post_ml']) }}

-- Collateral stress test (docs/05 §4). ILLUSTRATIVE, NOT A REGULATORY STRESS TEST.
-- Population: clean residential market sales of the last 36 complete months, marked to
-- market with the hedonic index (zone x type series where published, else type). A buyer is
-- in negative equity when the loan, held at origination (no amortisation: conservative),
-- exceeds the shocked current value. One row per segment x ready/off-plan x scenario x loan
-- basis. "Shock Pct" and "LTV Pct" are integers for the Power BI what-if slicers (docs/06):
-- Shock Pct is NULL on the replay rows, LTV Pct NULL on the CBUAE cap and actual-loan rows.
-- Under min_n purchases the share, count and AED are blank. Off-plan is never pooled with
-- ready: banks cap off-plan lending at 50% and most buyers pay the developer in
-- instalments, so an assumed LTV on the full price overstates the bank's exposure.
select
    initcap(g.segment_level) as "Segment Level",
    case
        when g.segment_level = 'dubai' then 'Dubai (all residential)'
        when g.segment_level = 'type' and g.property_type_key = 101 then 'Apartments'
        when g.segment_level = 'type' then 'Villas / Townhouses'
        when g.segment_level = 'zone' and g.property_type_key = 101 then g.zone || ': Apartments'
        when g.segment_level = 'zone' then g.zone || ': Villas / Townhouses'
        when g.property_type_key = 101 then coalesce(a.area_name, 'Unknown area') || ': Apartments'
        else coalesce(a.area_name, 'Unknown area') || ': Villas / Townhouses'
    end as "Segment",
    g.property_type_key as "Property Type Key",
    g.zone as "Zone",
    g.area_key as "Area Key",
    case when g.is_offplan then 'Off-Plan' else 'Ready' end as "Ready / Off-Plan",
    case g.scenario
        when 'grid' then 'Price shock'
        when 'replay_2014_2020' then 'Replay: 2014-2020 drawdown'
    end as "Scenario",
    g.shock_pct as "Shock Pct",
    round(g.applied_shock, 4) as "Applied Shock",
    case g.ltv_basis
        when 'grid' then 'Assumed LTV'
        when 'cbuae_cap' then 'CBUAE cap (expatriate, first home)'
        when 'actual_loan' then 'Registered loan (matched purchases)'
    end as "Loan Basis",
    g.ltv_pct as "LTV Pct",
    case
        when g.ltv_pct = 85 then '85% UAE national first home cap (worst case)'
        when g.ltv_pct is not null then g.ltv_pct || '%'
    end as "LTV Label",
    g.purchases as "Purchases",
    g.negative_equity_count as "Negative Equity Count",
    round(g.negative_equity_share, 4) as "Negative Equity Share",
    round(g.negative_equity_aed, 0) as "Negative Equity AED",
    round(g.loan_aed, 0) as "Loan AED",
    round(g.current_value_aed, 0) as "Current Value AED",
    round(g.index_zone_share, 4) as "Zone Index Share",
    g.is_published as "Is Published",
    g.window_start as "Purchases From",
    g.window_end as "Purchases To",
    g.model_version as "Model Version"
from {{ source('ml', 'stress_grid') }} as g
left join {{ ref('dim_area') }} as a on a.area_key = g.area_key
where g.model_version = '{{ var("stress_model_version") }}'
