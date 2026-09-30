{{ config(alias='dim_procedure') }}

-- DLD procedures with their category and market-sale / mortgage flags (seed_procedure_map).
select
    procedure_key as "Procedure Key",
    trans_group as "Transaction Group",
    procedure_name as "Procedure",
    procedure_category as "Procedure Category",
    procedure_category_description as "Procedure Category Description",
    is_market_sale as "Is Market Sale",
    is_new_mortgage as "Is New Mortgage",
    is_portfolio_mortgage as "Is Portfolio Mortgage",
    is_lease_to_own as "Is Lease to Own",
    amount_is_loan as "Amount Is Loan"
from {{ ref('dim_procedure') }}
