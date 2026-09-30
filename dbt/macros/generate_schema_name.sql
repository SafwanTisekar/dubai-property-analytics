{#
    Use the configured custom schema verbatim (silver, gold, rpt) instead of dbt's
    default "<target_schema>_<custom_schema>" (e.g. public_silver). The schemas are
    created and granted by sql/01_schemas_grants.sql, so dbt must land in exactly those.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
