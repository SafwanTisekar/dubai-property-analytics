{{ config(alias='dim_ready_offplan') }}

-- Ready / Off-Plan slicer (reg_type, a first-class dimension: CLAUDE.md). Facts carry the
-- same text in "Ready / Off-Plan"; rents are all ready, so rent_month isn't related.
select 'Ready' as "Ready / Off-Plan", 1 as "Ready / Off-Plan Order"
union all
select 'Off-Plan', 2
