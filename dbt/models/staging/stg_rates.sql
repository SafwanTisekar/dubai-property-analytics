-- Monthly rate drivers, one row per month (docs/02 §5). Rates are decimals (0.0525, not
-- 5.25; docs/01 §7). Brent is averaged from daily prices, skipping non-trading days ('').
-- EIBOR joins here once a CBUAE file is loaded (docs/08 Phase 1 open item).

with fed_funds as (

    select
        date_trunc('month', {{ safe_iso_date('observation_date') }})::date as month,
        {{ to_num('fedfunds') }} / 100 as fed_funds_rate
    from {{ source('bronze', 'rates_fedfunds') }}

),

brent as (

    select
        date_trunc('month', {{ safe_iso_date('observation_date') }})::date as month,
        avg({{ to_num('dcoilbrenteu') }}) as brent_usd,
        count({{ clean_text('dcoilbrenteu') }}) as brent_trading_days
    from {{ source('bronze', 'rates_brent') }}
    group by 1

)

select
    coalesce(f.month, b.month) as month,
    f.fed_funds_rate,
    round(b.brent_usd, 4) as brent_usd,
    b.brent_trading_days
from fed_funds as f
full outer join brent as b
    on b.month = f.month
