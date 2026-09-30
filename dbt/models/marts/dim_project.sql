-- One row per DLD project seen in the transactions, plus Unknown (-1) for the 26% of
-- lines with no project (C9). project_key = DLD project_number.
-- Built from the transaction register only: the DLD projects file (developer, status,
-- completion date) is deferred for v1, so there is no developer yet (docs/08 Phase 0).
-- A few projects are registered under more than one master project; the most frequent
-- one is kept (ties: alphabetical), and master_project_count shows where that happened.

with lines as (

    select project_number, project_name, master_project, txn_date
    from {{ ref('int_market_sales') }}
    where project_number is not null
    union all
    select project_number, project_name, master_project, txn_date
    from {{ ref('int_mortgages') }}
    where project_number is not null

),

ranked_names as (

    select
        project_number,
        project_name,
        master_project,
        row_number() over (
            partition by project_number
            order by count(*) desc, project_name, master_project
        ) as rank
    from lines
    group by project_number, project_name, master_project

),

stats as (

    select
        project_number,
        count(*) as transaction_lines,
        count(distinct master_project) as master_project_count,
        min(txn_date) as first_txn_date,
        max(txn_date) as last_txn_date
    from lines
    group by project_number

)

select
    s.project_number as project_key,
    s.project_number,
    coalesce(n.project_name, 'Project ' || s.project_number) as project_name,
    coalesce(n.master_project, 'Unknown') as master_project,
    s.master_project_count,
    s.transaction_lines,
    s.first_txn_date,
    s.last_txn_date
from stats as s
inner join ranked_names as n
    on n.project_number = s.project_number
    and n.rank = 1

union all

select -1, null, 'Unknown', 'Unknown', 0, 0, null, null
