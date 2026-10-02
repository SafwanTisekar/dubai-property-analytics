{{ config(alias='avm_performance', tags=['post_ml']) }}

-- AVM accuracy (docs/05 §1) per model x split x breakdown x segment. Metrics are on the
-- sale price in AED: MdAPE (headline), hit rates within 10% / 20%, MAPE, R² on ln(price),
-- and coverage (share of the segment's sales the model can value). "_common" breakdowns
-- are the head-to-head on the sales every model values. Price bands are by predicted
-- value; "Price Band Actual" bands by the sale price, which favours no model but builds
-- in regression to the mean. Segments under min_n scored sales are not published.
select
    p.model as "Model",
    case p.model
        when 'comps' then 'Comparable sales (6 months)'
        when 'comps_indexed' then 'Index-adjusted comparables (12 months)'
        when 'hedonic_ols' then 'Hedonic OLS (rolling monthly refit)'
        when 'lightgbm' then 'LightGBM'
    end as "Model Name",
    p.is_champion as "Is Champion",
    initcap(p.split) as "Split",
    initcap(replace(p.breakdown, '_', ' ')) as "Breakdown",
    p.segment as "Segment",
    p.n_total as "Sales in Segment",
    p.n_scored as "Sales Valued",
    {{ rpt_ratio("p.coverage") }} as "Coverage",
    {{ rpt_ratio("p.mdape") }} as "MdAPE",
    {{ rpt_ratio("p.hit10") }} as "Hit Rate 10 Pct",
    {{ rpt_ratio("p.hit20") }} as "Hit Rate 20 Pct",
    {{ rpt_ratio("p.mape") }} as "MAPE",
    {{ rpt_ratio("p.r2_log_price") }} as "R2 Log Price",
    p.model_version as "Model Version"
from {{ source('ml', 'avm_performance') }} as p
where p.model_version = '{{ var("avm_model_version") }}'
