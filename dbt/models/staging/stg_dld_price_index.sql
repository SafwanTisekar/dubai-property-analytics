-- DLD's official Residential Sale Index, long form: one row per month x segment x
-- frequency (docs/05 §2, validation only). The file is wide (all / flat / villa x monthly /
-- quarterly / yearly x index / price_index), so it is unpivoted here.
--
-- * index_ratio: DLD's dimensionless index, 1.000 at the base period (Jan 2012 monthly,
--   Q1 2012 quarterly, 2012 yearly). index_2012_100 rescales it to 100 for charts.
-- * typical_price_aed: DLD's "price index", an AED price level of a typical unit. Not a
--   rescaled index_ratio (the ratio between the two drifts), so validation uses index_ratio.
-- * Quarterly values sit on the quarter's last month, yearly values on December. Empty
--   cells arrive as NULL (the file leaves them unquoted), so rows without a value drop out.

with src as (

    select
        {{ safe_iso_date('first_date_of_month') }} as month_start,
        {{ clean_text('load_timestamp') }}::timestamp as loaded_at,
        _snapshot_date as snapshot_date,
        t.*
    from {{ source('bronze', 'dld_price_index') }} as t

),

long as (

    select
        s.month_start,
        v.segment,
        v.frequency,
        {{ to_num('v.index_text') }} as index_ratio,
        {{ to_num('v.price_text') }} as typical_price_aed,
        s.loaded_at as load_timestamp,
        s.snapshot_date
    from src as s
    cross join lateral (
        values
            ('all', 'monthly', s.all_monthly_index, s.all_monthly_price_index),
            ('all', 'quarterly', s.all_quarterly_index, s.all_quarterly_price_index),
            ('all', 'yearly', s.all_yearly_index, s.all_yearly_price_index),
            ('flat', 'monthly', s.flat_monthly_index, s.flat_monthly_price_index),
            ('flat', 'quarterly', s.flat_quarterly_index, s.flat_quarterly_price_index),
            ('flat', 'yearly', s.flat_yearly_index, s.flat_yearly_price_index),
            ('villa', 'monthly', s.villa_monthly_index, s.villa_monthly_price_index),
            ('villa', 'quarterly', s.villa_quarterly_index, s.villa_quarterly_price_index),
            ('villa', 'yearly', s.villa_yearly_index, s.villa_yearly_price_index)
    ) as v (segment, frequency, index_text, price_text)

)

select
    month_start,
    segment,
    frequency,
    index_ratio,
    round(index_ratio * 100, 2) as index_2012_100,
    typical_price_aed::numeric(18, 2) as typical_price_aed,
    load_timestamp,
    snapshot_date
from long
where index_ratio is not null
