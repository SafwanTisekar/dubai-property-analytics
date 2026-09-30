-- Monthly rate drivers from 2004 (dim_date start) to the latest month: Fed Funds (the AED
-- is pegged to the USD, so it is the fallback rate driver) and Brent. Rates are decimals
-- (0.0525, not 5.25; CLAUDE.md). EIBOR columns are NULL until a CBUAE file is loaded
-- (docs/04 §6, manual download); the columns exist now so the Power BI model won't change.

select
    month,
    fed_funds_rate::numeric(8, 6) as fed_funds_rate,
    null::numeric(8, 6) as eibor_1m,
    null::numeric(8, 6) as eibor_3m,
    null::numeric(8, 6) as eibor_6m,
    null::numeric(8, 6) as eibor_12m,
    brent_usd::numeric(10, 4) as brent_usd,
    brent_trading_days
from {{ ref('stg_rates') }}
where month between date '{{ var("dim_date_start") }}' and date '{{ var("dim_date_end") }}'
