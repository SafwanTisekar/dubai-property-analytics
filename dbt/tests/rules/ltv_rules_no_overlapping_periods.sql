-- seed_ltv_rules: a rule (borrower x property status x home number x value band) has at most
-- one cap in force on any day. Returns every pair of rows for the same rule whose effective
-- periods overlap. NULL effective_from / effective_to mean an open start / end.
select a.rule_id as rule_id_a, b.rule_id as rule_id_b,
       a.borrower, a.property_status, a.home_number, a.value_band
from {{ ref('seed_ltv_rules') }} as a
join {{ ref('seed_ltv_rules') }} as b
    on b.borrower = a.borrower
    and b.property_status = a.property_status
    and b.home_number = a.home_number
    and b.value_band = a.value_band
    and b.rule_id > a.rule_id
where daterange(a.effective_from, a.effective_to, '[]')
   && daterange(b.effective_from, b.effective_to, '[]')
