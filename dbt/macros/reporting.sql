{#
  Publishing rules for the rpt views (docs/06 §1). Kept as macros so every view applies
  them the same way.
#}

{# AED to whole dirhams as bigint: Power BI imports it as a Whole Number, which compresses
   far better than a decimal, and cards never show fils anyway. #}
{% macro rpt_aed(col) -%}
    round({{ col }})::bigint
{%- endmacro %}

{# Min-n rule (CLAUDE.md): a median from fewer than var('min_n') observations is not
   published. The n column is always published, so the gap is visible and explainable. #}
{% macro rpt_min_n_median(median_col, n_col) -%}
    case when {{ n_col }} >= {{ var('min_n') }} then round({{ median_col }})::bigint end
{%- endmacro %}

{# Shared slicer keys (docs/06 §2). Power BI relates facts to rpt.dim_bedrooms and
   rpt.dim_ready_offplan on these columns, so one Bedrooms slicer and one Ready / Off-Plan
   slicer filter every fact. Unknown bedrooms are -1, not NULL: a NULL key would land on
   Power BI's blank member, which a slicer can't label. #}
{% macro rpt_bedrooms_key(col) -%}
    coalesce({{ col }}, -1)::smallint
{%- endmacro %}

{% macro rpt_ready_offplan(col) -%}
    case when {{ col }} then 'Off-Plan' else 'Ready' end
{%- endmacro %}
