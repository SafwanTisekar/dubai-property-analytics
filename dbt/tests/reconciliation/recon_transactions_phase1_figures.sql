-- The published Phase 1 figures (seed_phase1_reconciliation) reproduced from silver, at
-- the precision they were published (AED bn to 0.1, exact counts). Checked only when
-- bronze holds exactly the Phase 1 snapshot; on other data (CI fixtures, a newer extract)
-- the gate returns no rows and recon_transactions_once_vs_phase1_rule does the work.
with expected as (
    select metric, trans_group, expected_value
    from {{ ref('seed_phase1_reconciliation') }}
    where dataset = 'transactions' and metric <> 'bronze_rows'
),
gate as (
    select (select count(*) from {{ source('bronze', 'dld_transactions') }})
         = (select expected_value from {{ ref('seed_phase1_reconciliation') }}
            where dataset = 'transactions' and metric = 'bronze_rows') as is_phase1_snapshot
),
by_group as (
    select trans_group,
        round(sum(actual_worth_aed) / 1e9, 1) as naive_total_bn,
        round((sum(actual_worth_aed) - sum(actual_worth_once_aed)) / 1e9, 1) as overstated_bn,
        count(distinct deal_group_id) filter (where is_repeated_deal_value) as repeated_groups,
        count(*) filter (where is_repeated_deal_value) as repeated_lines,
        count(distinct batch_group_id) as similar_size_groups,
        count(*) filter (where is_similar_size_batch) as similar_size_lines
    from {{ ref('int_transaction_deal_groups') }}
    group by 1
),
actual as (
    select trans_group, metric, value
    from by_group
    cross join lateral (values
        ('naive_total_bn', naive_total_bn),
        ('overstated_bn', overstated_bn),
        ('repeated_groups', repeated_groups::numeric),
        ('repeated_lines', repeated_lines::numeric),
        ('similar_size_groups', similar_size_groups::numeric),
        ('similar_size_lines', similar_size_lines::numeric)
    ) as v (metric, value)
)
select e.trans_group, e.metric, e.expected_value, a.value as actual_value
from expected as e
left join actual as a using (trans_group, metric)
where (select is_phase1_snapshot from gate)
  and a.value is distinct from e.expected_value
