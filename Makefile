# Dubai Property Analytics: one entry point for every pipeline step (CLAUDE.md "Commands").
# Targets marked [stub] are placeholders until their phase in docs/08 is built.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Load .env (if present) and export it, so psql, dbt and Python all see the same PG_* vars.
# In CI there is no .env; the workflow sets the variables directly.
-include .env
export

# Superuser for `make db`. Homebrew Postgres makes your macOS user a superuser and trusts
# local socket connections; in CI this is `postgres` with PGHOST/PGPASSWORD set.
ifeq ($(strip $(PG_ADMIN_USER)),)
PG_ADMIN_USER := $(USER)
endif

PG_DB ?= dubai_property

PSQL := psql -X -v ON_ERROR_STOP=1 -U $(PG_ADMIN_USER)
DBT  := cd dbt && uv run dbt
DBT_FLAGS := --profiles-dir .
PY   := uv run python -m dubai_property

# Where `make bronze` reads CSVs from. Use `make bronze BRONZE_ROOT=data/sample` (with
# BRONZE_FLAGS=--reset) to work against the sample instead of the full data.
BRONZE_ROOT ?= data/raw
BRONZE_FLAGS ?=

.PHONY: help setup db dbt-deps dbt-debug lint test \
        download bronze reconcile profile sample fixtures dbt dq kpi dictionary unzoned train score update pipeline

help:  ## List targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

# --- Implemented ----------------------------------------------------------------------

setup:  ## uv sync, pre-commit install, dbt packages
	@command -v uv >/dev/null || { echo "uv not found: brew install uv"; exit 1; }
	uv sync
	uv run pre-commit install
	$(MAKE) dbt-deps

db:  ## Create database, roles (dpa_owner, pbi_reader), schemas and grants (sql/*.sql)
	@[ -n "$$PG_PASSWORD" ] || { echo "PG_PASSWORD is empty: set it in .env"; exit 1; }
	@[ -n "$$PBI_READER_PASSWORD" ] || { echo "PBI_READER_PASSWORD is empty: set it in .env"; exit 1; }
	@# Passwords go in as psql variables (never echoed); the SQL quotes them with :'var'.
	@$(PSQL) -d postgres -v owner_pw="$$PG_PASSWORD" -v reader_pw="$$PBI_READER_PASSWORD" \
		-f sql/00_create_database.sql
	$(PSQL) -d $(PG_DB) -f sql/01_schemas_grants.sql
	@echo "Database $(PG_DB) ready: schemas bronze, silver, gold, ml, rpt."

dbt-deps:  ## Install dbt packages (dbt_utils, dbt_expectations)
	$(DBT) deps $(DBT_FLAGS)

dbt-debug:  ## Check the dbt connection and project
	$(DBT) debug $(DBT_FLAGS)

lint:  ## ruff lint + format check
	uv run ruff check .
	uv run ruff format --check .

test:  ## pytest + dbt test
	uv run pytest
	$(DBT) test $(DBT_FLAGS)

# --- Phase 1: ingestion, bronze, profiling (docs/04 §1) --------------------------------

download:  ## FRED rates -> data/raw/fred (EIBOR: files in data/raw/cbuae); DLD increments deferred
	$(PY).ingest.download_rates
	$(PY).ingest.download_dld_increment

bronze:  ## CSVs -> bronze.* via COPY (manifest skips loaded files), then reconcile counts
	$(PY).ingest.load_bronze --root $(BRONZE_ROOT) $(BRONZE_FLAGS)
	$(MAKE) reconcile

reconcile:  ## File record counts vs bronze row counts -> reports/bronze_reconciliation.md
	$(PY).quality.reconcile

profile:  ## Profile every bronze column + Phase 1 investigations -> reports/profile_*.md
	$(PY).quality.profile
	$(PY).quality.investigate

sample:  ## 2% sample stratified by year x area (whole deals/contracts) -> data/sample
	$(PY).ingest.sample

fixtures:  ## Rebuild the committed CI fixtures (~2k lines per table) -> tests/fixtures
	$(PY).ingest.fixtures

# --- Phase 2: dbt silver, gold and rpt (docs/04 §2-4) -----------------------------------
# CI runs the same targets on the fixtures: make bronze BRONZE_ROOT=tests/fixtures && make dbt

dbt:  ## dbt build (seeds, silver, gold, rpt, tests), then DQ report, KPI check, dictionary
	@# Seeds are tiny: reload them from scratch so an added seed column never needs a manual
	@# --full-refresh (dependent staging views are dropped and rebuilt by the build).
	$(DBT) seed --full-refresh $(DBT_FLAGS)
	$(DBT) build $(DBT_FLAGS)
	$(MAKE) dq kpi dictionary

dq:  ## Rows per step and per rule, Phase 1 reconciliation -> reports/dq_report.md
	$(PY).quality.dq_report

kpi:  ## Pre-ML KPIs from silver vs the rpt views -> reports/kpi_reconciliation.md (fails on a mismatch)
	$(PY).quality.kpi_reconciliation

dictionary:  ## Models, columns, types, docs and tests -> docs/data-dictionary.md
	$(PY).quality.data_dictionary

unzoned:  ## Worksheet of seed_area rows without a zone -> reports/unzoned_areas.md
	$(PY).quality.unzoned_areas

# --- Stubs (implemented in later phases, see docs/08) ---------------------------------

train:  ## [stub] AVM, hedonic index, yields, stress test, forecast (Phase 4)
	@echo "train: not implemented yet (Phase 4, docs/08)"

score:  ## [stub] write ml.* tables, then dbt build --select tag:post_ml (Phase 4)
	@echo "score: not implemented yet (Phase 4, docs/08)"

update:  ## [stub] incremental monthly refresh end to end (Phases 1-4)
	@echo "update: not implemented yet (Phases 1-4, docs/08)"

pipeline: download bronze dbt train score  ## Everything, in order
	@echo "pipeline: done"
