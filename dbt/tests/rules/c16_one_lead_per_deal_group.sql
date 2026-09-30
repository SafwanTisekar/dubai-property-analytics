-- C16: every deal has exactly one lead line, the lead carries the full value and the other
-- lines carry 0, so a sum of actual_worth_once_aed counts each deal exactly once.
select deal_group_id, count(*) as lines,
       count(*) filter (where is_deal_group_lead) as leads,
       min(deal_group_lines) as expected_lines
from {{ ref('int_transaction_deal_groups') }}
group by deal_group_id
having count(*) filter (where is_deal_group_lead) <> 1
    or count(*) <> min(deal_group_lines)
    or sum(actual_worth_once_aed) <> max(actual_worth_aed)
