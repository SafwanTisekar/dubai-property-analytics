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
        download bronze reconcile profile sample fixtures dbt dq kpi dictionary unzoned centroids \
        pbi-ready pbi-measures pbi-inventory eda train score model-reports update pipeline

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

dbt:  ## dbt build (seeds, silver, gold, rpt, tests; not the post_ml views), then DQ report, KPI check, dictionary
	@# Seeds are tiny: reload them from scratch so an added seed column never needs a manual
	@# --full-refresh (dependent staging views are dropped and rebuilt by the build).
	@# post_ml views read ml.* tables that only exist after make train: make score builds them.
	$(DBT) seed --full-refresh $(DBT_FLAGS)
	$(DBT) build --exclude tag:post_ml $(DBT_FLAGS)
	$(MAKE) dq kpi dictionary

dq:  ## Rows per step and per rule, Phase 1 reconciliation -> reports/dq_report.md
	$(PY).quality.dq_report

kpi:  ## Pre-ML KPIs from silver vs the rpt views -> reports/kpi_reconciliation.md (fails on a mismatch)
	$(PY).quality.kpi_reconciliation

dictionary:  ## Models, columns, types, docs and tests -> docs/data-dictionary.md
	$(PY).quality.data_dictionary

unzoned:  ## Worksheet of seed_area rows without a zone -> reports/unzoned_areas.md
	$(PY).quality.unzoned_areas

centroids:  ## Area centroids from OpenStreetMap Nominatim (cached) -> seed_area.csv, reports/area_centroids.md
	$(PY).ingest.geocode_areas

# --- Power BI connection (docs/03 §8) --------------------------------------------------
# Postgres listens on localhost and the Mac's Parallels Shared-network address. That
# address only exists while Parallels runs, so if Postgres started first (e.g. at login)
# it isn't listening there: restart it once Parallels is up, then prove pbi_reader works.

PBI_HOST ?= 10.211.55.2

pbi-ready:  ## Restart Postgres, then check Power BI's login (pbi_reader @ PBI_HOST) works
	@[ -n "$$PBI_READER_PASSWORD" ] || { echo "PBI_READER_PASSWORD is empty: set it in .env"; exit 1; }
	@if ! ifconfig | grep -q "inet $(PBI_HOST) "; then \
		echo "NOT READY: $(PBI_HOST) isn't on any interface. Start Parallels (the Windows VM) first, then run make pbi-ready again."; \
		exit 1; fi
	brew services restart postgresql@18
	@for i in $$(seq 1 30); do pg_isready -q -h $(PBI_HOST) -p $(PG_PORT) && break; sleep 1; done; \
	if ! pg_isready -q -h $(PBI_HOST) -p $(PG_PORT); then \
		echo "NOT READY: Postgres isn't listening on $(PBI_HOST):$(PG_PORT). Start Parallels first, then run make pbi-ready again (check listen_addresses in postgresql.conf)."; \
		exit 1; fi
	@if n=$$(PGPASSWORD="$$PBI_READER_PASSWORD" psql -X -At -h $(PBI_HOST) -p $(PG_PORT) -U pbi_reader \
			-d $(PG_DB) -c "select count(*) from rpt.report_info" 2>&1) && [ "$$n" = "1" ]; then \
		echo "OK: Power BI can connect. Server $(PBI_HOST):$(PG_PORT), database $(PG_DB), user pbi_reader (password: PBI_READER_PASSWORD in .env)."; \
	else \
		echo "NOT READY: pbi_reader query failed: $$n"; \
		echo "Check pg_hba.conf (host $(PG_DB) pbi_reader 10.211.55.0/24 scram-sha-256) and that make dbt has built rpt."; \
		exit 1; fi

pbi-measures:  ## Export the semantic model's measures (TMDL) -> powerbi/measures.dax, a review copy
	$(PY).powerbi.tmdl

pbi-inventory:  ## Every report page and visual (PBIR) -> powerbi/VISUALS.md, a review copy
	$(PY).powerbi.pbir

# --- Phase 3: exploratory analysis (docs/08) -----------------------------------------
# Needs the gold tables and rpt views on the full data (make dbt). Notebooks only call
# src/dubai_property/analysis; the run fails if an executed notebook is over 1 MB.

eda:  ## Execute notebooks/0*.ipynb in place -> reports/figures/*.png (findings: reports/findings.md)
	$(PY).analysis.run_notebooks

# --- Phase 4: models (docs/05) ----------------------------------------------------------
# train fits the models and writes their ml.* tables with COPY (4a: hedonic price index and
# gross yields; 4b: the AVM; 4c: the forecast, incl. its rolling-origin backtest). score
# runs the stress test (no fitting: it marks the recent book to market against the index),
# checks every ml.* table exists, then builds the rpt views over them (dbt tag post_ml).
#
# AVM tuning: by default the saved Optuna study (artifacts/avm/best_params.json) is reused
# when the features are unchanged, else 20 trials run (docs/05 §8). Force a re-tune with
# AVM_TRIALS=20; AVM_TRIALS=2 for a quick run (CI on the fixtures).
AVM_TRIALS ?=

train:  ## Fit the models (hedonic index, yields, AVM, forecast) and write ml.* via COPY
	$(PY).models.hedonic_index
	$(PY).models.yields
	$(PY).models.avm $(if $(AVM_TRIALS),--trials $(AVM_TRIALS))
	$(PY).models.forecast

score:  ## Stress test -> ml.stress_*, check every ml.* table, dbt build --select tag:post_ml, then the KPI / card checklist
	$(PY).models.score
	$(MAKE) kpi

model-reports:  ## Model reports from ml.* -> reports/price_index.md, yields.md, avm_model_card.md, stress_test.md, forecast.md, figures
	$(PY).models.report_4a
	$(PY).models.report_avm
	$(PY).models.report_4c

# --- Stubs (implemented in later phases, see docs/08) ---------------------------------

update:  ## [stub] incremental monthly refresh end to end (Phases 1-4)
	@echo "update: not implemented yet (Phases 1-4, docs/08)"

pipeline: download bronze dbt train score  ## Everything, in order
	@echo "pipeline: done"
