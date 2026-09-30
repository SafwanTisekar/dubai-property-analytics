-- C11 reconciliation on ANY data: the sum of allocated rent equals the sum of annual_amount
-- counted once per contract straight from bronze (the Phase 1 method), and the contract
-- and multi-line counts agree. Requires annual_amount on every line (true in Phase 1;
-- otherwise C12 annualises and this test flags the difference for review).
with bronze_lines as (
    select distinct on (contract_id, line_number) contract_id, line_number, annual_amount
    from {{ source('bronze', 'dld_rent_contracts') }}
    order by contract_id, line_number, _snapshot_date desc, _ingested_at desc, _row_hash
),
bronze_contracts as (
    select contract_id, count(*) as lines, min(nullif(annual_amount, '')::numeric) as annual
    from bronze_lines
    group by 1
),
reference as (
    select count(*) as contracts,
           count(*) filter (where lines > 1) as multi_line_contracts,
           sum(lines) filter (where lines > 1) as multi_line_lines,
           sum(annual) as once_per_contract_aed
    from bronze_contracts
),
silver as (
    select count(distinct contract_id) as contracts,
           count(distinct contract_id) filter (where is_multi_unit) as multi_line_contracts,
           count(*) filter (where is_multi_unit) as multi_line_lines,
           sum(annual_rent_alloc_aed) as once_per_contract_aed
    from {{ ref('int_rent_contracts') }}
)
select r.*, s.*
from reference as r cross join silver as s
where r.contracts <> s.contracts
   or r.multi_line_contracts <> s.multi_line_contracts
   or r.multi_line_lines is distinct from s.multi_line_lines
   or abs(r.once_per_contract_aed - s.once_per_contract_aed) > 1
