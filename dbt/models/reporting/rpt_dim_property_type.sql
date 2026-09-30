{{ config(alias='dim_property_type') }}

-- Conformed property type shared by sales, rents and the aggregates. The id columns are
-- sort-by columns for the two labels.
select
    property_type_key as "Property Type Key",
    usage_group as "Usage Group",
    usage_group_id as "Usage Group Order",
    property_class as "Property Class",
    property_class_id as "Property Class Order",
    property_type_label as "Property Type",
    property_class_description as "Property Class Description"
from {{ ref('dim_property_type') }}
