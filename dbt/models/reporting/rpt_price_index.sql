{{ config(alias='price_index', tags=['post_ml']) }}

-- Hedonic price index (docs/05 §2): rolling-window time-dummy regression on clean
-- residential market sales, chained, Jan 2019 = 100 (Q1 2019 for quarterly segments). One
-- row per segment x published period: periods with fewer than min_n sales were never
-- written. Changes are decimals (0.05 = +5%). Drawdown is from the running peak (<= 0).
select
    p.segment_id as "Segment Key",
    case
        when p.segment_level = 'dubai' then 'Dubai (all residential)'
        when p.segment_level = 'type' and p.property_type_key = 101 then 'Apartments'
        when p.segment_level = 'type' then 'Villas / Townhouses'
        when p.property_type_key = 101 then p.zone || ': Apartments'
        else p.zone || ': Villas / Townhouses'
    end as "Segment",
    initcap(p.segment_level) as "Segment Level",
    p.property_type_key as "Property Type Key",
    p.zone as "Zone",
    initcap(p.frequency) || 'ly' as "Frequency",
    p.period_start as "Period Start",
    p.n_obs as "Sales",
    round(p.index_value, 2) as "Index Value",
    round(p.index_3m, 2) as "Index 3M Average",
    round(p.mom, 4) as "Change on Previous Period",
    round(p.yoy, 4) as "YoY Change",
    round(p.vol_12m, 4) as "Volatility 12M",
    round(p.running_peak, 2) as "Running Peak",
    round(p.drawdown, 4) as "Drawdown",
    p.episode_id as "Drawdown Episode",
    p.is_partial_period as "Is Partial Period",
    p.model_version as "Model Version"
from {{ source('ml', 'fct_price_index') }} as p
where p.model_version = '{{ var("hedonic_model_version") }}'
