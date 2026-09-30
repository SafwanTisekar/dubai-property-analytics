-- Gold = silver for rents: fct_rent_contract holds every int_rent_contracts line with the
-- same allocated rent (full precision) and the same market-rent population.
with silver as (
    select
        count(*) as lines,
        sum(annual_rent_alloc_aed) as rent_alloc,
        count(*) filter (where is_market_rent) as market_rent_lines
    from {{ ref('int_rent_contracts') }}
),

gold as (
    select
        count(*) as lines,
        sum(annual_rent_alloc_aed) as rent_alloc,
        count(*) filter (where is_market_rent) as market_rent_lines
    from {{ ref('fct_rent_contract') }}
)

select s.*, g.lines as gold_lines, g.rent_alloc as gold_rent_alloc, g.market_rent_lines as gold_market
from silver as s
cross join gold as g
where s.lines <> g.lines
   or s.rent_alloc is distinct from g.rent_alloc
   or s.market_rent_lines <> g.market_rent_lines
