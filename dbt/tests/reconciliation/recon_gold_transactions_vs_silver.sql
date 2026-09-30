-- Gold = silver for transactions: fct_transaction must hold exactly the lines of
-- int_market_sales + int_mortgages, with the same AED, per trans_group. Returns one row per
-- group where any figure differs (AED compared to the fils: gold is numeric(18,2) and the
-- silver values are whole fils, so the cast loses nothing).
with silver as (
    select
        trans_group,
        count(*) as lines,
        sum(actual_worth_aed) as actual_worth_aed,
        sum(actual_worth_once_aed) as aed_once,
        count(*) filter (where is_market_sale) as market_sales,
        count(*) filter (where is_clean_market_sale) as clean_sales,
        0::numeric as loans_once,
        0::numeric as portfolio_once
    from {{ ref('int_market_sales') }}
    group by 1
    union all
    select
        trans_group,
        count(*),
        sum(actual_worth_aed),
        sum(actual_worth_once_aed),
        0,
        0,
        coalesce(sum(mortgage_amount_once_aed), 0),
        coalesce(sum(portfolio_mortgage_value_once_aed), 0)
    from {{ ref('int_mortgages') }}
    group by 1
),

gold as (
    select
        trans_group,
        count(*) as lines,
        sum(actual_worth_aed) as actual_worth_aed,
        sum(aed_counted_once) as aed_once,
        count(*) filter (where is_market_sale) as market_sales,
        count(*) filter (where is_clean_market_sale) as clean_sales,
        coalesce(sum(mortgage_amount_once_aed), 0) as loans_once,
        coalesce(sum(portfolio_mortgage_value_once_aed), 0) as portfolio_once
    from {{ ref('fct_transaction') }}
    group by 1
)

select
    coalesce(s.trans_group, g.trans_group) as trans_group,
    s.lines as silver_lines, g.lines as gold_lines,
    s.aed_once as silver_aed_once, g.aed_once as gold_aed_once
from silver as s
full outer join gold as g
    on g.trans_group = s.trans_group
where s.lines is distinct from g.lines
   or s.actual_worth_aed is distinct from g.actual_worth_aed
   or s.aed_once is distinct from g.aed_once
   or s.market_sales is distinct from g.market_sales
   or s.clean_sales is distinct from g.clean_sales
   or s.loans_once is distinct from g.loans_once
   or s.portfolio_once is distinct from g.portfolio_once
