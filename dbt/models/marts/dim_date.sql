-- Day-grain calendar for Power BI time intelligence (docs/06 §2: marked as the date table).
-- Runs from dim_date_start to dim_date_end (past the data, for Phase 4 forecasts). Facts
-- join on the date itself; monthly aggregates join on the first day of the month.
-- is_after_snapshot marks days after the data snapshot date (int_data_snapshot), so the
-- report can hide empty future periods.

with days as (

    select d::date as date
    from generate_series(
        date '{{ var("dim_date_start") }}',
        date '{{ var("dim_date_end") }}',
        interval '1 day'
    ) as d

)

select
    date,
    extract(year from date)::smallint as year,
    extract(quarter from date)::smallint as quarter,
    extract(month from date)::smallint as month_num,
    to_char(date, 'FMMonth') as month_name,
    to_char(date, 'Mon') as month_short,
    date_trunc('month', date)::date as month_start,
    date_trunc('quarter', date)::date as quarter_start,
    to_char(date, 'YYYY-MM') as year_month,
    to_char(date, 'YYYY "Q"Q') as year_quarter,
    extract(isodow from date)::smallint as day_of_week,  -- 1 = Monday
    to_char(date, 'FMDay') as day_name,
    extract(day from date) = 1 as is_month_start,
    date > s.data_snapshot_date as is_after_snapshot
from days
cross join {{ ref('int_data_snapshot') }} as s
