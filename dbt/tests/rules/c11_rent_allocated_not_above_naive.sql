-- docs/04 §4 rent de-duplication test: after allocation, total rent can't exceed the naive
-- sum over lines (equal only if there are no multi-line contracts).
select sum(annual_rent_alloc_aed) as allocated, sum(annual_rent_contract_aed) as naive
from {{ ref('int_rent_contracts') }}
having sum(annual_rent_alloc_aed) > sum(annual_rent_contract_aed) + 0.01
