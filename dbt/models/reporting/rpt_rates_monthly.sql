{{ config(alias='rates_monthly') }}

-- Monthly rate drivers. Rates are decimals (format as % in Power BI); EIBOR is blank until
-- a CBUAE file is loaded.
select
    month as "Month",
    fed_funds_rate as "Fed Funds Rate",
    eibor_1m as "EIBOR 1M",
    eibor_3m as "EIBOR 3M",
    eibor_6m as "EIBOR 6M",
    eibor_12m as "EIBOR 12M",
    brent_usd as "Brent USD"
from {{ ref('fct_rates_monthly') }}
