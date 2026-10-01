{{ config(alias='forecast', tags=['post_ml']) }}

-- Market outlook (docs/05 §5): monthly hedonic index (Jan 2019 = 100) and clean residential
-- sales volume, actuals to the last complete month, then a 12-month SARIMAX forecast per
-- rate scenario (Fed Funds as the EIBOR proxy, lagged; scenarios step from the first
-- forecast month, so they only diverge after the lag). Intervals are 80% / 95%; they assume
-- the model is right and the backtest coverage (rpt.forecast_backtest) shows how far that
-- holds. Index forecasts are rounded to 2 decimals, volumes to whole sales.
select
    case f.target when 'index' then 'Price index' else 'Sales volume' end as "Target",
    case f.segment
        when 'dubai' then 'Dubai (all residential)'
        when 'apartment' then 'Apartments'
        when 'villa' then 'Villas / Townhouses'
    end as "Segment",
    f.month as "Month",
    case f.scenario
        when 'actual' then 'Actual'
        when 'rates_flat' then 'Rates flat'
        when 'rates_up_100bp' then 'Rates +100bp'
        when 'rates_down_100bp' then 'Rates -100bp'
    end as "Scenario",
    f.is_forecast as "Is Forecast",
    round(f.actual, case when f.target = 'index' then 2 else 0 end) as "Actual",
    round(f.forecast, case when f.target = 'index' then 2 else 0 end) as "Forecast",
    round(f.lower_80, case when f.target = 'index' then 2 else 0 end) as "Lower 80",
    round(f.upper_80, case when f.target = 'index' then 2 else 0 end) as "Upper 80",
    round(f.lower_95, case when f.target = 'index' then 2 else 0 end) as "Lower 95",
    round(f.upper_95, case when f.target = 'index' then 2 else 0 end) as "Upper 95",
    round(f.rate_path, 4) as "Fed Funds Rate Path",
    f.model_version as "Model Version"
from {{ source('ml', 'forecast') }} as f
where f.model_version = '{{ var("forecast_model_version") }}'
