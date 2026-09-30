{{ config(alias='dim_project') }}

-- DLD projects seen in the transactions (developer arrives with the projects file later).
select
    project_key as "Project Key",
    project_name as "Project",
    master_project as "Master Project",
    first_txn_date as "First Transaction Date",
    last_txn_date as "Last Transaction Date",
    transaction_lines as "Transaction Lines"
from {{ ref('dim_project') }}
