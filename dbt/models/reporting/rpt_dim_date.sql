{{ config(alias='dim_date') }}

-- Calendar for Power BI (mark as date table on "Date").
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
    is_after_snapshot as "Is After Snapshot"
from {{ ref('dim_date') }}
