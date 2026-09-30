-- Row-count reconciliation, bronze -> silver. Silver removes rows in one place only (C1
-- de-duplication in stg_transactions), and the two intermediate models split
-- stg_transactions without losing or repeating a line. Returns a row per broken check.
with counts as (
    select
        (select count(distinct transaction_id) from {{ source('bronze', 'dld_transactions') }})
            as bronze_distinct_ids,
        (select count(*) from {{ ref('stg_transactions') }}) as stg_rows,
        (select count(*) from {{ ref('int_transaction_deal_groups') }}) as deal_group_rows,
        (select count(*) from {{ ref('int_market_sales') }}) as market_sales_rows,
        (select count(*) from {{ ref('int_mortgages') }}) as mortgage_rows,
        (select count(*) from {{ ref('int_market_sales') }} as s
         join {{ ref('int_mortgages') }} as m using (transaction_id)) as overlap_rows
)
select * from counts
where stg_rows <> bronze_distinct_ids
   or deal_group_rows <> stg_rows
   or market_sales_rows + mortgage_rows <> stg_rows
   or overlap_rows <> 0
