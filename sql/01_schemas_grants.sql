-- 01_schemas_grants.sql
-- Medallion schemas and privileges (docs/03 §3). Run as a superuser against the
-- `dubai_property` database (see `make db`). Idempotent: safe to re-run.

\set ON_ERROR_STOP on

-- One schema per layer, all owned by the pipeline role so dbt and the Python loaders
-- (which connect as dpa_owner) can create, replace and drop objects in them.
create schema if not exists bronze authorization dpa_owner;  -- raw text copies of source CSVs
create schema if not exists silver authorization dpa_owner;  -- typed, cleaned, flagged (dbt)
create schema if not exists gold   authorization dpa_owner;  -- star schema marts (dbt)
create schema if not exists ml     authorization dpa_owner;  -- model outputs (Python)
create schema if not exists rpt    authorization dpa_owner;  -- reporting views for Power BI (dbt)

-- If the schemas already existed with another owner, bring them back to dpa_owner.
alter schema bronze owner to dpa_owner;
alter schema silver owner to dpa_owner;
alter schema gold   owner to dpa_owner;
alter schema ml     owner to dpa_owner;
alter schema rpt    owner to dpa_owner;

-- Lock down `public` so nothing lands there by accident and pbi_reader can't see it.
revoke all on schema public from public;

-- ---------------------------------------------------------------------------------
-- pbi_reader: SELECT on rpt only (docs/01 §7).
-- Power BI must never see bronze/silver/gold/ml, so no USAGE is granted on them.
-- ---------------------------------------------------------------------------------
grant usage on schema rpt to pbi_reader;

-- Objects that already exist in rpt.
grant select on all tables in schema rpt to pbi_reader;

-- Objects created later. dbt runs as dpa_owner, so every future rpt view it builds
-- (including after a full drop/recreate) is readable by pbi_reader automatically.
-- "on tables" covers views and materialized views too.
alter default privileges for role dpa_owner in schema rpt
    grant select on tables to pbi_reader;
