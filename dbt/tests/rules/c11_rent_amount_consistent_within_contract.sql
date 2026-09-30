{{ config(severity='warn') }}
-- C11 assumes every line of a contract repeats the same amount (100% of multi-line contracts
-- in Phase 1). Warn if a new snapshot breaks that, because the allocation becomes ambiguous.
select contract_id
from {{ ref('int_rent_contracts') }}
where is_amount_inconsistent
group by contract_id
