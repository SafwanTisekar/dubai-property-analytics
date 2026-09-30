-- C11: line_count is the real number of lines, and line_number runs 1..n with no gaps
-- or repeats (true for every contract in Phase 1). A failure means the allocation
-- denominator is wrong for that contract.
select contract_id, min(line_count) as line_count, max(line_number) as max_line_number,
       count(distinct line_number) as distinct_line_numbers
from {{ ref('int_rent_contracts') }}
group by contract_id
having min(line_count) <> max(line_number)
    or min(line_count) <> count(distinct line_number)
    or min(line_number) <> 1
