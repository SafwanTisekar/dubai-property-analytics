{{ config(alias='feature_importance', tags=['post_ml']) }}

-- What drives the AVM (docs/05 §1): mean |SHAP| per feature on a sample of test sales, in
-- log points of the predicted price (0.05 ~ 5%), with LightGBM's split gain alongside.
-- "Feature Label" is the readable name (seed_avm_feature_label); the raw name is kept.
select
    f.feature as "Feature",
    coalesce(l.feature_label, f.feature) as "Feature Label",
    initcap(f.feature_group) as "Feature Group",
    round(f.mean_abs_shap, 6) as "Mean Abs SHAP",
    round(f.gain, 2) as "Split Gain",
    f.rank as "Rank",
    f.model_version as "Model Version"
from {{ source('ml', 'feature_importance') }} as f
left join {{ ref('seed_avm_feature_label') }} as l on l.feature = f.feature
where f.model_version = '{{ var("avm_model_version") }}'
