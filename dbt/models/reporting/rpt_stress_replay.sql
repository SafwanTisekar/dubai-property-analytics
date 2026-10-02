{{ config(alias='stress_replay', tags=['post_ml']) }}

-- Historical replay for the stress test (docs/05 §4): each published index series' deepest
-- fall from its running peak between Jan 2014 and Dec 2021 (the 2014 -> 2020 episode).
-- "Used In Replay" is false for zone series published only after the June 2014 peak (they
-- would measure a smaller, later fall); their sales take the type series' drawdown. Zone
-- series are noisier than type series, so their drawdowns are deeper. No 2008-11 replay:
-- the index starts in 2011 (docs/05 §8).
select
    r.segment_id as "Segment Key",
    case
        when r.segment_level = 'dubai' then 'Dubai (all residential)'
        when r.segment_level = 'type' and r.property_type_key = 101 then 'Apartments'
        when r.segment_level = 'type' then 'Villas / Townhouses'
        when r.property_type_key = 101 then r.zone || ': Apartments'
        else r.zone || ': Villas / Townhouses'
    end as "Segment",
    initcap(r.segment_level) as "Segment Level",
    r.property_type_key as "Property Type Key",
    r.zone as "Zone",
    initcap(r.frequency) || 'ly' as "Frequency",
    r.first_period as "Published From",
    r.peak_period as "Peak",
    round(r.peak_index, 2) as "Peak Index",
    r.trough_period as "Trough",
    round(r.trough_index, 2) as "Trough Index",
    {{ rpt_ratio("r.drawdown") }} as "Drawdown",
    r.is_used as "Used In Replay",
    r.note as "Note",
    r.model_version as "Model Version"
from {{ source('ml', 'stress_replay') }} as r
where r.model_version = '{{ var("stress_model_version") }}'
