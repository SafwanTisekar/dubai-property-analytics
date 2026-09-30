-- C16: portfolio deals that repeat one deal value on every unit line.
-- One row per transaction line (all groups: Sales, Mortgages, Gifts).
--
-- The bulk export gives every line its own transaction_id, so a portfolio deal can't be
-- read from the data; it has to be inferred. This is the Phase 1 rule
-- (REPEATED_VALUE_GROUP in src/dubai_property/quality/investigate.py) in SQL:
--
--   candidate group = same trans_group, procedure, date (as registered), value and ID-year
--   repeated value  = lines > 1
--                     and ID sequence span <= 2 x lines   (registered in one batch)
--                     and max size / min size > 1.10      (different units, same "price")
--
-- A 822 sq m and a 1,540 sq m unit can't both be worth the same AED 6.79bn, so the value
-- is the deal total, repeated. `actual_worth_once_aed` keeps it on the first line only,
-- so AED totals count each deal once. Contiguous groups whose sizes are within 10% are
-- probably identical units at identical prices; they are flagged (`is_similar_size_batch`)
-- but not corrected. The reconciliation tests check this model against the Phase 1 SQL.

with lines as (

    select
        transaction_id,
        trans_group,
        procedure_id,
        instance_date_raw,
        actual_worth_aed,
        id_year,
        id_seq,
        area_sqm
    from {{ ref('stg_transactions') }}

),

-- Window functions rather than group-by-then-join: one sort, and NULL keys (none today)
-- still group together exactly as they did in the Phase 1 GROUP BY.
candidate_groups as (

    select
        *,
        count(*) over deal as group_lines,
        max(id_seq) over deal - min(id_seq) over deal + 1 as id_span,
        -- NULL when a line has 0 sq m, which leaves the group unflagged (as in Phase 1).
        max(area_sqm) over deal / nullif(min(area_sqm) over deal, 0) as area_ratio,
        -- The group's first line by DLD running number: its id becomes the group id.
        first_value(transaction_id) over (deal order by id_seq, transaction_id)
            as lead_transaction_id
    from lines
    window deal as (
        partition by trans_group, procedure_id, instance_date_raw, actual_worth_aed, id_year
    )

),

classified as (

    select
        *,
        coalesce(
            group_lines > 1
            and id_span <= {{ var('repeated_value_span_factor') }} * group_lines
            and area_ratio > {{ var('repeated_value_area_ratio') }},
            false
        ) as is_repeated_deal_value,
        coalesce(
            group_lines > 1
            and id_span <= {{ var('repeated_value_span_factor') }} * group_lines
            and area_ratio <= {{ var('repeated_value_area_ratio') }},
            false
        ) as is_similar_size_batch
    from candidate_groups

)

select
    transaction_id,
    trans_group,
    actual_worth_aed,

    is_repeated_deal_value,
    -- Lines of one repeated-value deal share the lead line's id; every other line is its
    -- own deal. So `count(distinct deal_group_id)` counts deals, not lines.
    case when is_repeated_deal_value then lead_transaction_id else transaction_id end
        as deal_group_id,
    case when is_repeated_deal_value then group_lines else 1 end as deal_group_lines,
    (not is_repeated_deal_value or transaction_id = lead_transaction_id)
        as is_deal_group_lead,
    -- AED counted once per deal: the full value on the lead line, 0 on the repeats.
    case
        when not is_repeated_deal_value or transaction_id = lead_transaction_id
            then actual_worth_aed
        else 0
    end as actual_worth_once_aed,

    is_similar_size_batch,
    case when is_similar_size_batch then lead_transaction_id end as batch_group_id,
    case when is_similar_size_batch then group_lines end as batch_group_lines
from classified
