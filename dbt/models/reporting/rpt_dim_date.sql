{{ config(alias='dim_date') }}

-- Calendar for Power BI (mark as date table on "Date"). dim_date runs past the data (to the
-- end of the forecast horizon), so the Year slicer is limited to "Is Data Year" (years up to
-- the snapshot year) and shows "Year Label", which marks the snapshot year as partial
-- ("2026 (to 25 Sep)"). Both come from the snapshot date, nothing is hard-coded.
with snapshot as (
    select max(date) as as_of from {{ ref('dim_date') }} where not is_after_snapshot
)

select
    date as "Date",
    year as "Year",
    quarter as "Quarter",
    month_num as "Month Number",
    month_name as "Month",
    month_short as "Month Short",
    month_start as "Month Start",
    quarter_start as "Quarter Start",
    year_month as "Year Month",
    year_quarter as "Year Quarter",
    day_of_week as "Day of Week",
    day_name as "Day Name",
    is_month_start as "Is Month Start",
    is_after_snapshot as "Is After Snapshot",
    case
        when d.year = extract(year from s.as_of)
            then d.year::text || ' (to ' || to_char(s.as_of, 'FMDD Mon') || ')'
        else d.year::text
    end as "Year Label",
    d.year <= extract(year from s.as_of) as "Is Data Year"
from {{ ref('dim_date') }} as d
cross join snapshot as s
