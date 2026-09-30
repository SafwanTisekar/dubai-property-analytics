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

.PHONY: help setup db dbt-deps dbt-debug lint test \
        download bronze dbt train score update sample pipeline

help:  ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
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

# --- Stubs (implemented in later phases, see docs/08) ---------------------------------

download:  ## [stub] DLD increments + rates -> data/raw (Phase 1)
	@echo "download: not implemented yet (Phase 1, docs/08)"

bronze:  ## [stub] raw CSVs -> bronze.* via COPY (Phase 1)
	@echo "bronze: not implemented yet (Phase 1, docs/08)"

sample:  ## [stub] 2% stratified CSV sample -> data/sample (Phase 1)
	@echo "sample: not implemented yet (Phase 1, docs/08)"

dbt:  ## [stub] dbt build -> silver, gold, rpt (pre-ML) (Phase 2)
	@echo "dbt: not implemented yet (Phase 2, docs/08)"

train:  ## [stub] AVM, hedonic index, yields, stress test, forecast (Phase 4)
	@echo "train: not implemented yet (Phase 4, docs/08)"

score:  ## [stub] write ml.* tables, then dbt build --select tag:post_ml (Phase 4)
	@echo "score: not implemented yet (Phase 4, docs/08)"

update:  ## [stub] incremental monthly refresh end to end (Phases 1-4)
	@echo "update: not implemented yet (Phases 1-4, docs/08)"

pipeline: download bronze dbt train score  ## Everything, in order
	@echo "pipeline: done"
