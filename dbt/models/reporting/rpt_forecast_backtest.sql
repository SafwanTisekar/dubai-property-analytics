{{ config(alias='forecast_backtest', tags=['post_ml']) }}

-- Forecast backtest (docs/05 §5): rolling origin over the last 24 complete months. Each
-- origin's index forecast is fitted on the real-time vintage of that month (sales before
-- it only), not on today's revised index, and scored on the change it predicted. MAPE /
-- MdAPE per horizon; coverage = share of actuals inside the SARIMAX 80% / 95% interval.
-- "Is Baseline" marks the better of the two naive models for that target and segment.
select
    case b.target when 'index' then 'Price index' else 'Sales volume' end as "Target",
    case b.segment
        when 'dubai' then 'Dubai (all residential)'
        when 'apartment' then 'Apartments'
        when 'villa' then 'Villas / Townhouses'
    end as "Segment",
    case b.model
        when 'naive_rw' then 'Naive (last value)'
        when 'naive_seasonal' then 'Seasonal naive'
        when 'sarimax' then 'SARIMAX + lagged Fed Funds'
    end as "Model",
    b.horizon as "Horizon Months",
    b.n_origins as "Origins Scored",
    round(b.mape, 4) as "MAPE",
    round(b.mdape, 4) as "MdAPE",
    round(b.coverage_80, 4) as "Coverage 80",
    round(b.coverage_95, 4) as "Coverage 95",
    b.is_baseline as "Is Baseline",
    b.model_version as "Model Version"
from {{ source('ml', 'forecast_backtest') }} as b
where b.model_version = '{{ var("forecast_model_version") }}'
