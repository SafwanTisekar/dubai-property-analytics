{#
  Largest plausible unit area (sq m) for a conformed property class (seed_property_class
  ids: 1 Apartment, 2 Villa / Townhouse, 4 Office, 5 Retail; everything else uses the
  general cap). Used by C21 for rents and by the area-weighted price population for sales.
  Above it, the area is a community, plot or whole-building figure, not the unit's.
#}
{% macro class_area_cap(class_id_col) -%}
    case {{ class_id_col }}
        when 1 then {{ var('area_cap_apartment_sqm') }}
        when 2 then {{ var('area_cap_villa_sqm') }}
        when 4 then {{ var('area_cap_office_retail_sqm') }}
        when 5 then {{ var('area_cap_office_retail_sqm') }}
        else {{ var('area_cap_other_sqm') }}
    end
{%- endmacro %}
