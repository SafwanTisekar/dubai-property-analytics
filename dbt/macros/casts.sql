{#
  Typed casts used by staging. Bronze holds every value as text, and DLD quotes every
  field, so a missing value arrives as '' rather than NULL (phase1_findings §0). Every
  cast therefore goes through nullif(trim(x), '') first.

  Numbers are cast directly: Phase 1 found 100% of non-blank values numeric, so a cast
  error means the source format changed, and the build should stop loudly.
  Dates are cast defensively: known-bad values exist (Hijri years, far-future rent end
  dates), so an unparseable date becomes NULL and the model raises a date flag instead.
#}

{% macro clean_text(col) -%}
    nullif(trim({{ col }}), '')
{%- endmacro %}

{% macro to_num(col, type='numeric') -%}
    nullif(trim({{ col }}), '')::{{ type }}
{%- endmacro %}

{# Integer IDs are exported as '975.00' in some columns (project_number), so go via numeric. #}
{% macro to_int(col) -%}
    nullif(trim({{ col }}), '')::numeric::integer
{%- endmacro %}

{# ISO YYYY-MM-DD only (the one format Phase 1 found). pg_input_is_valid (PG 16+) rejects
   impossible dates such as 2020-02-30 without raising. #}
{% macro safe_iso_date(col) -%}
    case
        when trim({{ col }}) ~ '^\d{4}-\d{2}-\d{2}$' and pg_input_is_valid(trim({{ col }}), 'date')
            then trim({{ col }})::date
    end
{%- endmacro %}

{% macro to_bool01(col) -%}
    case trim({{ col }}) when '1' then true when '0' then false end
{%- endmacro %}
