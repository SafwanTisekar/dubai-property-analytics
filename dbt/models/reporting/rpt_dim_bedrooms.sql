{{ config(alias='dim_bedrooms') }}

-- Bedrooms slicer shared by transactions, area_month, rent_month and avm_score (docs/06 §2).
-- One row per key from -1 (unknown: land, commercial, or not recorded) to 20, so every fact
-- value has a row (relationship tests below); 7 and more share the label "7+ BR".
select
    k::smallint as "Bedrooms Key",
    case
        when k = -1 then 'Unknown'
        when k = 0 then 'Studio'
        when k <= 6 then k || ' BR'
        else '7+ BR'
    end as "Bedrooms",
    least(k, 7)::smallint as "Bedrooms Order"
from generate_series(-1, 20) as k
