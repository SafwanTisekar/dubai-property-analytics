-- The published Phase 1 rent figures reproduced from silver: contracts, multi-line
-- contracts and lines, naive vs once-per-contract AED (bn, 0.1). Gated on the Phase 1
-- snapshot like recon_transactions_phase1_figures.
with expected as (
    select metric, expected_value
    from {{ ref('seed_phase1_reconciliation') }}
    where dataset = 'rents' and metric <> 'bronze_rows'
),
gate as (
    select (select count(*) from {{ source('bronze', 'dld_rent_contracts') }})
         = (select expected_value from {{ ref('seed_phase1_reconciliation') }}
            where dataset = 'rents' and metric = 'bronze_rows') as is_phase1_snapshot
),
totals as (
    select count(distinct contract_id)::numeric as contracts,
           count(distinct contract_id) filter (where is_multi_unit)::numeric as multi_line_contracts,
           count(*) filter (where is_multi_unit)::numeric as multi_line_lines,
           round(sum(annual_amount_aed) / 1e9, 1) as naive_total_bn,
           round(sum(annual_rent_alloc_aed) / 1e9, 1) as once_per_contract_bn
    from {{ ref('int_rent_contracts') }}
),
actual as (
    select metric, value
    from totals
    cross join lateral (values
        ('contracts', contracts),
        ('multi_line_contracts', multi_line_contracts),
        ('multi_line_lines', multi_line_lines),
        ('naive_total_bn', naive_total_bn),
        ('once_per_contract_bn', once_per_contract_bn)
    ) as v (metric, value)
)
select e.metric, e.expected_value, a.value as actual_value
from expected as e
left join actual as a using (metric)
where (select is_phase1_snapshot from gate)
  and a.value is distinct from e.expected_value
