-- Every published index segment is exactly 100 in its base period (Jan 2019, or Q1 2019 for
-- quarterly segments) and has that period: the base is what makes segments comparable.
{{ config(tags=['post_ml']) }}
with segments as (
    select distinct "Segment Key" as segment_key from {{ ref('rpt_price_index') }}
),

base as (
    select "Segment Key" as segment_key, "Index Value" as index_value
    from {{ ref('rpt_price_index') }}
    where "Period Start" = date '{{ var("index_base_month") }}'
)

select s.segment_key, b.index_value
from segments as s
left join base as b on b.segment_key = s.segment_key
where b.index_value is null or b.index_value <> 100
