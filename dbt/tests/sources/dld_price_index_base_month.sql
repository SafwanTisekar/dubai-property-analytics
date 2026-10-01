-- DLD's monthly index is 1.000 in Jan 2012 for every segment (profiled 2026-10-01). If a
-- new DLD file moves the base, the validation rebasing (docs/05 §2) must be revisited.
-- The synthetic CI fixture has no Jan 2012 row, so the test has nothing to check there.
select segment, index_ratio
from {{ ref('stg_dld_price_index') }}
where frequency = 'monthly'
    and month_start = date '2012-01-01'
    and index_ratio <> 1
