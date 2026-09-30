-- Financing: every Mortgages-group line (C10, C16, C17, C18). Analysed separately from
-- prices (CLAUDE.md): nothing here feeds the price index, yields or the AVM.
--
-- C10: `actual_worth` is the LOAN amount for Mortgage Registration and Delayed Mortgage
-- (median 0.795 / 0.800 of the same-day sale price, following the CBUAE LTV caps;
-- phase1_findings §2). For every other mortgage procedure (pre-registration, modify,
-- transfer, portfolio, development, lease finance, lease-to-own) the meaning is mixed or
-- unverified, so `amount_is_loan` is false, `mortgage_amount_aed` is NULL, and the row
-- counts as volume only. The recorded value stays in `actual_worth_aed`.
-- C16: portfolio loans repeat one value per unit line; `*_once_aed` count it once.
--
-- `is_new_mortgage` marks individual new mortgages, which include refinancing: the
-- secondary indicator "new mortgages per 100 market sales". The headline purchase-mortgage
-- share pairs a mortgage with its same-day sale (int_purchase_mortgage_pairs). Portfolio
-- registrations (`is_portfolio_mortgage`: one loan over several units, often a developer
-- or investor) are kept apart: count them per deal (count distinct deal_group_id) and sum
-- `portfolio_mortgage_value_once_aed`, the recorded deal value once per deal. Their amount
-- is not a verified loan (C10), so it is labelled a value, not a loan amount.

with mortgages as (

    select
        t.*,
        g.is_repeated_deal_value,
        g.deal_group_id,
        g.deal_group_lines,
        g.is_deal_group_lead,
        g.actual_worth_once_aed,
        g.is_similar_size_batch,
        g.batch_group_id,
        g.batch_group_lines
    from {{ ref('stg_transactions') }} as t
    inner join {{ ref('int_transaction_deal_groups') }} as g
        on g.transaction_id = t.transaction_id
    where t.trans_group = 'Mortgages'

)

select
    transaction_id,
    trans_group,
    procedure_id,
    procedure_name,
    procedure_category,
    is_new_mortgage,
    is_portfolio_mortgage,
    is_lease_to_own,
    amount_is_loan,
    txn_date,
    instance_date_raw,
    is_date_invalid,
    is_pre_2004,

    property_type,
    property_sub_type,
    property_usage,
    is_residential,
    reg_type,
    is_offplan,
    area_id,
    area_name,
    zone,
    building_name,
    project_number,
    project_name,
    master_project,
    has_project,
    rooms_en,
    bedrooms,
    room_class,
    area_sqm,

    actual_worth_aed,
    case when amount_is_loan then actual_worth_aed end as mortgage_amount_aed,
    case when amount_is_loan then actual_worth_once_aed end as mortgage_amount_once_aed,
    case when is_portfolio_mortgage then actual_worth_once_aed end
        as portfolio_mortgage_value_once_aed,

    is_repeated_deal_value,
    deal_group_id,
    deal_group_lines,
    is_deal_group_lead,
    actual_worth_once_aed,
    is_similar_size_batch,
    batch_group_id,
    batch_group_lines,

    snapshot_date,
    source_file
from mortgages
