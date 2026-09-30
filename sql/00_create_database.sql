-- 00_create_database.sql
-- Creates the login roles and the UTF-8 database. Run as a superuser against the
-- `postgres` maintenance database (see `make db`). Idempotent: safe to re-run.
--
-- Required psql variables (passed by the Makefile from .env):
--   owner_pw   password for dpa_owner  (pipeline: Python loaders + dbt)
--   reader_pw  password for pbi_reader (Power BI, read-only on rpt.*)
--
-- CREATE ROLE / CREATE DATABASE have no IF NOT EXISTS, so each statement is generated
-- by a SELECT that returns a row only when the object is missing, then run by \gexec.

\set ON_ERROR_STOP on

-- Store passwords as SCRAM hashes (Power BI connects over the Parallels network with
-- scram-sha-256, docs/03 §8).
set password_encryption = 'scram-sha-256';

-- dpa_owner owns every schema and object. Deliberately not a superuser: the pipeline
-- should not be able to change server settings or other databases.
select 'create role dpa_owner login nosuperuser nocreatedb nocreaterole'
where not exists (select from pg_roles where rolname = 'dpa_owner')
\gexec

-- pbi_reader is what Power BI logs in as. Its rights are granted in 01_schemas_grants.sql.
select 'create role pbi_reader login nosuperuser nocreatedb nocreaterole'
where not exists (select from pg_roles where rolname = 'pbi_reader')
\gexec

-- Set passwords on every run so rotating a password in .env only needs `make db`.
alter role dpa_owner with password :'owner_pw';
alter role pbi_reader with password :'reader_pw';

-- UTF-8 is required for the Arabic (_ar) source columns. template0 lets us choose the
-- encoding/locale explicitly. 'C' collation gives byte-order sorting, which is fast and
-- identical across macOS and the Linux CI container (no locale-dependent test results).
select 'create database dubai_property owner dpa_owner encoding ''UTF8'' '
       'lc_collate ''C'' lc_ctype ''C'' template template0'
where not exists (select from pg_database where datname = 'dubai_property')
\gexec

-- Nobody connects unless explicitly granted (PUBLIC gets CONNECT by default).
revoke all on database dubai_property from public;
grant connect, temporary on database dubai_property to dpa_owner;
grant connect on database dubai_property to pbi_reader;
