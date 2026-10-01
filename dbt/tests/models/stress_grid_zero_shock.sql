{{ config(tags=['post_ml']) }}

-- At a 0% shock a buyer can only be in negative equity if the index has fallen since the
-- purchase by more than (1 - LTV). The deepest fall a published series shows in the window
-- bounds that: at 50% LTV no one can be under water unless an index halved. Rows fail.
select segment_level, property_type_key, zone, area_key, is_offplan, negative_equity_count
from {{ source('ml', 'stress_grid') }}
where model_version = '{{ var("stress_model_version") }}'
  and scenario = 'grid' and shock_pct = 0 and ltv_basis = 'grid' and ltv_pct = 50
  and negative_equity_count > 0
