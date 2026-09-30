-- Row-count reconciliation for rents: int_rent_contracts has one row per distinct
-- (contract_id, line_number) in bronze (C1 is the only step that removes rows).
with counts as (
    select
        (select count(*) from (select distinct contract_id, line_number
                               from {{ source('bronze', 'dld_rent_contracts') }}) as d)
            as bronze_distinct_lines,
        (select count(*) from {{ ref('int_rent_contracts') }}) as silver_rows
)
select * from counts where bronze_distinct_lines <> silver_rows
