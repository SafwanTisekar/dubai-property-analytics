-- One row per DLD procedure, keyed on (trans_group, procedure_id) as in seed_procedure_map
-- (C2). procedure_key is a stable integer held in the seed, so adding a procedure later
-- never renumbers the existing ones.

select
    pm.procedure_key,
    pm.trans_group,
    pm.procedure_id,
    pm.procedure_name_en as procedure_name,
    pm.procedure_category,
    pc.description as procedure_category_description,
    pm.is_market_sale,
    pm.is_lease_to_own,
    pm.is_new_mortgage,
    pm.is_portfolio_mortgage,
    pm.amount_is_loan
from {{ ref('seed_procedure_map') }} as pm
left join {{ ref('seed_procedure_category') }} as pc
    on pc.procedure_category = pm.procedure_category
