# 08 – Roadmap & Claude Code Playbook

Work one phase at a time. Start each phase in a fresh Claude Code session (or `/clear`) and use **plan mode** (Shift+Tab) for the first prompt. Estimated effort: **4–6 weeks part-time**.

---

## Phase 0: Setup & decisions (½ day)

- [x] Power BI Desktop: Windows VM under Parallels (docs/03 §8)
- [x] PostgreSQL 18 installed via Homebrew (2026-09-29)
- [x] Postgres service running (`brew services start postgresql@18`), `psql` on PATH, pgAdmin or DBeaver installed (docs/03 §6). PG 18.6 + DBeaver 26.2.1 (2026-09-30)
- [x] Work account on own domain (Zoho Mail) signs in to Power BI Service
- [x] Power BI Pro trial started 2026-09-29 (expiry recorded below). See docs/03 §9
- [x] Admin access confirmed (admin takeover via DNS TXT if the tenant is unmanaged) and **Publish to web** enabled
- [x] Throwaway report published to web and rendering in a private browser window (tested 2026-09-29)
- [x] Download the DLD bulk files manually if needed (Dubai Pulse `dld_transactions-open`, `dld_rent_contracts-open`, projects, buildings, units, lookups) into `data/raw/dld/<dataset>/`. Done 2026-09-30: transactions (2 files, 1,788,150 rows) and rents (11 files, ~10.5M lines). **Deferred:** projects, buildings, units and lookups are optional for v1 and not downloaded yet
- [x] Public GitHub repo connected to the project folder (kept out of OneDrive/iCloud sync). Don't commit until Phase 0 has created `.gitignore`

**Prompt**
```
Read CLAUDE.md and every file in docs/. Scaffold the repository per docs/03 §5 (package name dubai_property):
uv-managed pyproject.toml (Python 3.11) with the stack in CLAUDE.md, a Makefile with all targets from
CLAUDE.md (stub the unimplemented ones), .gitignore, .env.example (PG_* settings), pre-commit with ruff,
config.py, db.py (psycopg 3 connection, SQLAlchemy engine and connectorx URI built from .env),
sql/00_create_database.sql and sql/01_schemas_grants.sql per docs/03 §3/§5 (UTF-8 database dubai_property;
roles dpa_owner and pbi_reader; schemas bronze, silver, gold, ml, rpt; pbi_reader gets SELECT on rpt only,
including default privileges), a working `make db`, an empty dbt-postgres project (profiles.yml reading
env vars) with dbt_utils and dbt_expectations, and a GitHub Actions ci.yml running ruff + pytest with a
postgres:18 service container. No pipeline logic yet. Show the plan first.
```
**Done when:** `make setup`, `make db`, `uv run pytest` and `dbt debug` all pass, the five schemas are visible in pgAdmin/DBeaver, and the first commit is pushed.

---

## Phase 1: Ingestion, bronze & profiling (2–3 days)

**Prompt**
```
Implement Phase 1 per docs/02 and docs/04 §1: load_bronze.py (every CSV in data/raw/dld/<dataset>/ →
bronze.<dataset> with all columns as text via psycopg COPY, BOM/encoding-safe, metadata columns, manifest
so re-runs skip loaded files, ANALYZE after load), download_dld_increment.py (monthly date windows from DLD
Open Data; if automated download isn't possible, skip and rely on manually dropped files) and
download_rates.py (FRED FEDFUNDS and DCOILBRENTEU via the CSV endpoint; EIBOR from files in data/raw/cbuae),
loading rates into bronze the same way. Log row counts to reports/ingest_log.csv and verify file row counts
equal bronze row counts. Write quality/profile.py to profile every bronze column
(SQL-based: null %, distinct count, min/max, top values) into reports/profile_*.md. Specifically investigate and document: (1) the distinct procedure_name_en values
with counts, (2) whether actual_worth on mortgage rows is the loan amount, (3) how multi-property rent
contracts repeat amounts, (4) date formats. Build `make sample` (small CSV samples in data/sample for CI). Fill in docs/02 §7 with actual numbers.
```
**Done when:** bronze tables are loaded and reconciled to the files, profiles are written, docs/02 §7 is complete, and the four investigations are answered in `reports/phase1_findings.md`.

---

## Phase 2: dbt silver & gold (3–4 days)

**Prompt**
```
Implement Phase 2 per docs/04 §2–4: seeds (procedure_map, rooms_map, area with zones, ltv_rules with a
source-citation column left for me to verify), staging, intermediate (int_market_sales, int_mortgages,
int_rent_contracts) applying rules C1–C15 as flags (typing happens in staging), gold marts except the
post_ml ones with dbt indexes on the big facts, and rpt views for the gold tables. Add YAML
docs and all tests, including the reconciliation and rent de-duplication tests. Generate reports/dq_report.md
(rows affected per rule) and docs/data-dictionary.md from the dbt YAML. Run on the sample first, then the
full data, and report timings.
```
**Done when:** `dbt build` passes on full data, reconciliation holds, and the DQ report and dictionary are generated.

---

## Phase 3: EDA (2 days)

**Prompt**
```
Create notebooks 01_market_cycles, 02_financing_mix, 03_prices_and_rents that query gold via
SQLAlchemy/connectorx (aggregate in SQL, not pandas) and
answer Q1–Q4 and Q9 from docs/01, with charts saved to reports/figures/. Include an explicit mix-shift
example (raw median vs like-for-like). End each notebook with 3–5 quantified findings and collect them in
reports/findings.md.
```

---

## Phase 4: Models (5–7 days)

**4a: Hedonic index + yields**
```
Implement hedonic_index.py and yields.py per docs/05 §2–3. Validate the index against DLD's official
Residential Price Index (I'll place it in data/raw/dld/price_index/) and write reports/price_index.md.
Write fct_price_index and agg_yield_quarter with the min-n rule.
```
**4b: AVM**
```
Implement features (as-of lag features, no look-ahead, with a pytest proving it), split.py, avm_baseline.py
and avm_lgbm.py per docs/05 §1. Evaluate on the out-of-time test set by segment (MdAPE, ±10/±20% hit rates,
vs baseline), run SHAP, and write reports/avm_model_card.md. Stop and investigate if results look too good
(see CLAUDE.md).
```
**4c: Stress test + forecast**
```
Implement stress_test.py (shock × LTV grid plus historical drawdown replay) and forecast.py (seasonal naive
vs SARIMAX with lagged EIBOR, rolling-origin backtest, rate scenarios) per docs/05 §4–5. Write
reports/stress_test.md, then score.py to write all ml.* tables and build the post_ml marts.
```
**Done when:** the model cards and reports are complete, the AVM beats the baseline (or the result is honestly explained), and the index validates against DLD's.

**Stretch:** developer HHI and handover pipeline; area segmentation; rent-vs-buy calculator.

---

## Phase 5: Power BI (5–7 days)

**Prompt**
```
Finalise the rpt.* views per docs/06 §1 (friendly names, only needed columns, Power BI-friendly types,
AED rounded, _ar columns excluded) and confirm pbi_reader can read them and nothing else. Configure
postgresql.conf / pg_hba.conf guidance for the Parallels network (docs/03 §8) as a checklist in
powerbi/CONNECT.md. Write tests/test_kpi_reconciliation.py for every KPI in docs/01 §4 → reports/kpi_reconciliation.md,
powerbi/theme.json and powerbi/measures.dax with every measure from docs/06 §3 (integer-based what-if
values). Also expose area centroids from seed_area in rpt.dim_area for the map.
```
Then, in Power BI Desktop (Parallels), connect to PostgreSQL as pbi_reader (import mode), build the six pages per docs/06 §4–5, save as PBIP, publish, and create the Publish-to-web embed code.

**Done when:** the cards match `kpi_reconciliation.md`, every visual is under 1 s, and the embed URL is recorded below.

---

## Phase 6: Website (3–4 days)

**Prompt**
```
Build the static site in website/ per docs/07: index, case-study, methodology, data, about; responsive
Power BI iframe from website/config.js with a screenshot/GIF fallback; all numbers drawn from
reports/*.md (no invented figures); DLD CC BY 4.0 attribution; pages.yml deploy to GitHub Pages;
Lighthouse ≥ 90 via Playwright.
```

---

## Phase 7: Polish & launch (1–2 days)

- [ ] README with the architecture image, results table and GIF
- [ ] CI green; v1.0 release with the PBIX
- [ ] Docs reviewed against final results; decision logs filled in
- [ ] LinkedIn post + quantified CV bullet
- [ ] Set a monthly reminder to run `make update` and republish

---

## Tracking

| Phase | Status | Started | Finished | Notes |
|---|---|---|---|---|
| 0 Setup | ◐ | 2026-09-30 | | Scaffold done: `make setup`, `make db` (idempotent), `uv run pytest` (12 passed incl. pbi_reader grant tests) and `dbt debug` pass locally on PG 18.6 / dbt 1.12.5. Pending: first push + green CI |
| 1 Ingestion | ☐ | | | |
| 2 dbt | ☐ | | | |
| 3 EDA | ☐ | | | |
| 4 Models | ☐ | | | |
| 5 Power BI | ☐ | | | |
| 6 Website | ☐ | | | |
| 7 Launch | ☐ | | | |

| Publishing record | Value |
|---|---|
| Power BI tenant/account | |
| Publish-to-web URL | |
| Published on | |
| Licence/trial expires | Pro trial started 2026-09-29; expiry: _check under profile icon → trial days remaining_ |
| Website URL | |
| Data as of | |
