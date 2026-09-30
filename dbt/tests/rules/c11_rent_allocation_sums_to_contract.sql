-- C11: the per-line allocations of a contract add back to exactly one contract amount.
-- Returns contracts where they don't (tolerance: rounding in numeric division).
select
    contract_id,
    sum(annual_rent_alloc_aed) as allocated,
    min(annual_rent_contract_aed) as contract_amount
from {{ ref('int_rent_contracts') }}
group by contract_id
having abs(sum(annual_rent_alloc_aed) - min(annual_rent_contract_aed)) > 0.01
