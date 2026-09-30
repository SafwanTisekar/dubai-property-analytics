-- C16 reconciliation on ANY data (the CI fixtures included). Recomputes the Phase 1
-- repeated-value rule directly on bronze with the SQL of quality/investigate.py
-- (SETUP_TXN + REPEATED_VALUE_GROUP), after the same C1 de-duplication, and compares it
-- with silver per transaction group: AED counted once, groups and lines. Exact match
-- required. The investigate.py thresholds (2 x lines, 1.10) are the dbt vars' defaults.
with latest as (
    select *
    from (
        select *, row_number() over (partition by transaction_id
                                     order by _snapshot_date desc, _ingested_at desc, _row_hash) as rn
        from {{ source('bronze', 'dld_transactions') }}
    ) as d
    where rn = 1
),
txn_value_groups as (
    select trans_group_en as grp, procedure_name_en as procedure, instance_date,
           actual_worth::numeric as worth, split_part(transaction_id, '-', 3) as id_year,
           count(*) as lines,
           max(split_part(transaction_id, '-', 4)::int)
             - min(split_part(transaction_id, '-', 4)::int) + 1 as id_span,
           max(procedure_area::numeric) / nullif(min(procedure_area::numeric), 0) as area_ratio
    from latest
    group by 1, 2, 3, 4, 5
),
reference as (
    select grp as trans_group,
        sum(worth * lines) as naive_aed,
        sum(worth * lines)
          - coalesce(sum(worth * (lines - 1)) filter (
                where lines > 1 and id_span <= 2 * lines and area_ratio > 1.10), 0) as once_aed,
        count(*) filter (where lines > 1 and id_span <= 2 * lines and area_ratio > 1.10)
            as repeated_groups,
        coalesce(sum(lines) filter (where lines > 1 and id_span <= 2 * lines
                                    and area_ratio > 1.10), 0) as repeated_lines,
        count(*) filter (where lines > 1 and id_span <= 2 * lines and area_ratio <= 1.10)
            as similar_groups,
        coalesce(sum(lines) filter (where lines > 1 and id_span <= 2 * lines
                                    and area_ratio <= 1.10), 0) as similar_lines
    from txn_value_groups
    group by 1
),
silver as (
    select trans_group,
        sum(actual_worth_aed) as naive_aed,
        sum(actual_worth_once_aed) as once_aed,
        count(distinct deal_group_id) filter (where is_repeated_deal_value) as repeated_groups,
        count(*) filter (where is_repeated_deal_value) as repeated_lines,
        count(distinct batch_group_id) as similar_groups,
        count(*) filter (where is_similar_size_batch) as similar_lines
    from {{ ref('int_transaction_deal_groups') }}
    group by 1
)
select r.trans_group, r.*, s.*
from reference as r
full outer join silver as s using (trans_group)
where r.naive_aed is distinct from s.naive_aed
   or r.once_aed is distinct from s.once_aed
   or r.repeated_groups is distinct from s.repeated_groups
   or r.repeated_lines is distinct from s.repeated_lines
   or r.similar_groups is distinct from s.similar_groups
   or r.similar_lines is distinct from s.similar_lines
