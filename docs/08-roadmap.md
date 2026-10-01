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

- [x] Bronze loaded and reconciled to the files (`reports/bronze_reconciliation.md`, 15/15 files match)
- [x] Profiles written (`reports/profile_*.md`)
- [x] docs/02 §7 complete
- [x] Four investigations answered (`reports/phase1_findings.md`), plus portfolio double-counting quantified
- [ ] EIBOR: download CBUAE EIBOR history as CSV into `data/raw/cbuae/`, then `make bronze`

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

Phase 2 is split. **2a = silver** (seeds, staging, intermediate, DQ report, CI fixtures); **2b = gold + rpt** (marts with indexes, rpt views, `seed_ltv_rules`, `docs/data-dictionary.md`).

**2a checklist (silver)**
- [x] Postgres server settings from docs/03 §7 applied and verified (2026-09-30)
- [x] Seeds: `seed_procedure_map` (58 pairs) + `seed_procedure_category`, `seed_rooms_map`, `seed_rent_subtype_map`, `seed_area` (265 IDs), `seed_phase1_reconciliation`
- [x] Staging (`stg_transactions`, `stg_rent_contracts`, `stg_rates`) and intermediate (`int_transaction_deal_groups`, `int_market_sales`, `int_mortgages`, `int_rent_contracts`) with YAML docs and tests; rules C1–C22 (docs/04 §2)
- [x] `reports/dq_report.md` (`make dq`): rows per step, rows and AED per rule, population waterfalls, Phase 1 reconciliation
- [x] Reconciliation: every Phase 1 AED total and count reproduced exactly on full data
- [x] CI fixtures committed (`tests/fixtures/`, `make fixtures`); CI runs `make bronze BRONZE_ROOT=tests/fixtures && make dbt`
- [x] Mortgage share = individual new mortgages only; portfolio registrations flagged `is_portfolio_mortgage` and reported separately (dq_report §5)
- [x] CI green on 92b6191 (fixtures loaded, `make dbt` passes)
- [x] All 265 areas zoned (42 by the owner, 2026-09-30); `make unzoned` lists 0
- [x] 2b (see below)

**2b checklist (gold + rpt)**
- [x] Seeds: conformed property type (`seed_property_class`, `seed_property_usage_map`, `seed_property_type_map`), `procedure_key` in `seed_procedure_map`, empty centroid columns in `seed_area`, `seed_ltv_rules` (verified by the owner 2026-09-30 against the CBUAE rulebook, with effective dates and the pre-2020 regime; see docs/04 Decisions)
- [x] Dimensions: `dim_date` (day, 2004-01-01 → 2027-12-31), `dim_area`, `dim_property_type` (conformed), `dim_procedure`, `dim_project` (no developer yet)
- [x] Facts: `fct_transaction` (all lines, `aed_counted_once`), `fct_rent_contract` (all lines, allocated rent, market-rent flag), `fct_rates_monthly` (EIBOR columns NULL); indexed per docs/03 §7
- [x] Aggregates: `agg_area_month`, `agg_rent_month` (additive, medians with n, Σ value / Σ area)
- [x] rpt views (10), Title Case, AED whole dirhams, medians blank under min-n; pbi_reader reads rpt only (`tests/test_rpt_access.py`)
- [x] Tests: keys and relationships on every fact / agg → dim; gold = silver (`recon_gold_*`), aggregates = facts (`recon_agg_*`); `tests/test_kpi_reconciliation.py` → `reports/kpi_reconciliation.md` (0 mismatches; residential apartment area-weighted vs median within ±40% every year from 2010)
- [x] Owner review: per-class C21 area caps, area-weighted KPI on residential apartments + villas, data snapshot date (2026-09-25) ends the scope
- [x] `docs/data-dictionary.md` (`make dictionary`), docs/04 §3 and Decisions updated
- [x] CI green on 5076e27 ([run 36736326132](https://github.com/SafwanTisekar/dubai-property-analytics/actions/runs/36736326132)): fixtures through `make dbt`, then rpt access + KPI reconciliation. The first 2b push (1bd2800) failed: `make kpi` ran the apartment sanity check on the ~2k-line fixtures; the check now applies only from 100k transaction lines
- [x] `seed_ltv_rules` verified by the owner against the CBUAE rulebook (2026-09-30/10-01): current caps from 2020-04-08 (Board Resolution 31/2/2020), pre-2020 regime from Circular 31/2013 (2013-10-28 to 2020-04-07; gazette date not verified), with no-overlap and range tests. CI green on fa05bd2 ([run 36773158323](https://github.com/SafwanTisekar/dubai-property-analytics/actions/runs/36773158323))
- [ ] Phase 5: centroids in `seed_area`, DAX rewritten against rpt column names

**2b timings and rpt row counts**: full data, 16 GB M-series Mac, 4 dbt threads, final build (per-class C21 caps and the data snapshot date). `make dbt` **7 min 43 s** wall time: `dbt build` 6 min 37 s for 10 seeds, 16 tables, 13 views and 190 tests (gold: `fct_rent_contract` ~50 s, `fct_transaction` ~12 s, `agg_rent_month` ~8 s, `agg_area_month` ~2 s; the slowest step is still silver `int_rent_contracts`, ~140 s), then `make dq` ~45 s, `make kpi` 15 s, `make dictionary` < 1 s. Gold on disk: `fct_rent_contract` 2.6 GB, `fct_transaction` 0.6 GB. Fixture build in CI: seconds.

| rpt view | Rows |
|---|---|
| `rpt.transactions` | 1,769,938 (gold 1,788,150 less 18,208 pre-2004 and 4 Hijri-dated lines) |
| `rpt.rent_month` | 392,190 |
| `rpt.area_month` | 120,799 |
| `rpt.dim_date` | 8,766 |
| `rpt.dim_project` | 3,421 |
| `rpt.rates_monthly` | 273 |
| `rpt.dim_area` | 266 |
| `rpt.dim_property_type` | 66 |
| `rpt.dim_procedure` | 58 |
| `rpt.report_info` | 1 (Data As Of 2026-09-25) |

Phase 2b changed two silver rules (docs/04 Decisions): C21 per-class rent area caps (85,298 lines) and C18 `is_start_after_snapshot` (24,223 lines). Market-rent lines went from 3,601,613 (2a) to 3,593,480.

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

**Checklist**
- [x] `src/dubai_property/analysis/` (`market_cycles`, `financing`, `prices_rents`, `plotting`, `common`): every function aggregates in SQL over gold / rpt and returns a small frame; `fct_rent_contract` and `fct_transaction` never reach pandas
- [x] Three notebooks executed with `make eda` (01 market cycles 344 KB, 02 financing mix 351 KB, 03 prices and rents 740 KB; the run fails over 1 MB). They only call `analysis` and plot
- [x] 16 charts in `reports/figures/` (one style: colour-blind-safe slots, one y-axis per panel, 2026 marked partial, DLD CC BY 4.0 footer)
- [x] Q1 incl. the 2009 spike test (registration backlog under Law No. 13 of 2008), Q2 incl. observed LTV and portfolio mortgages, Q3 incl. the mix-shift example, Q4 preview (yields, min-n)
- [x] `reports/findings.md`: executive summary, every finding with chart, function and caveat, sanity check vs DLD's published 2023–2025 totals (within ~1% on value)
- [x] `tests/test_analysis.py` (15 tests: pure logic + every query on the DB), passing on full data and on the CI fixtures (scratch DB); added to the post-build CI step
- [x] Q9 (developer HHI) deferred: needs the DLD projects file (developer names)
- [x] **Revision after owner review (2026-09-30):**
  - [x] Mortgage KPI redefined as the purchase-mortgage share of ready sales (`int_purchase_mortgage_pairs`, gold flags, rpt columns); new mortgages per 100 market sales kept as secondary; KPI reconciliation, DQ report §5, docs/01 §4, docs/04 Decisions and docs/06 measures updated
  - [x] Villa AED/sq m area basis checked (villa areas mix plot and built-up sizes): "villas passed apartments" withdrawn, growth quoted on the bedroom-known subset and per unit
  - [x] 2026 momentum (Jan–Aug vs 2025, by type and zone) with registration-lag checks (daily tail, published-vs-extracted)
- [x] CI green on 831502c ([run 36759956450](https://github.com/SafwanTisekar/dubai-property-analytics/actions/runs/36759956450)): fixtures through `make dbt`, then rpt access, KPI reconciliation and the analysis queries

---

## Phase 4: Models (5–7 days)

**4a: Hedonic index + yields**
```
Implement hedonic_index.py and yields.py per docs/05 §2–3. Validate the index against DLD's official
Residential Price Index (I'll place it in data/raw/dld/price_index/) and write reports/price_index.md.
Write fct_price_index and agg_yield_quarter with the min-n rule.
```

**4a checklist**
- [x] DLD "Residential Properties Sale Index" (data.dubai) profiled and loaded (`make bronze BRONZE_FLAGS="--dataset price_index"`, owner-approved; 159 rows, only `bronze.dld_price_index` added, 16/16 files reconcile), `stg_dld_price_index` (long form, base-month test), README.txt note. Its data ends in **May 2024** (the 2026-09-01 stamp is the load time)
- [x] `models/hedonic_index.py`: time-dummy hedonic regression on clean residential sales (villas: bedroom-known only), **rolling-window (36 months, step 12) chained index** from **Jan 2011** (owner decisions after the material robustness gap and the 2009–10 backlog finding, docs/05 §8). 18 segments published (Dubai, apartments, villas monthly; 15 zone × type, 8 monthly + 7 quarterly), Jan 2019 = 100, min-n per period, noise gate; YoY, MoM, 3-month mean, 12-month volatility, drawdown, episodes → `ml.fct_price_index` (2,432 rows, COPY)
- [x] Robustness: pooled vs rolling windows (material: up to −11% level, +11 pp YoY on apartments; off-plan premium +6% → +38%), reported in `reports/price_index.md`
- [x] Validation vs DLD (2012–2024-05): timing-aligned YoY r **0.93 Dubai, 0.92 apartments, 0.91 villas** (target ≥ 0.9 met); raw month-for-month 0.72 / 0.70 / 0.68, ours leads by ~6 months; divergences explained; mix-shift chart and table
- [x] Episodes as found: one 2014→2020 Dubai episode (−24%, recovered Nov 2022) plus a 2011 dip; villas fell 11% from their Dec 2025 peak to Jul 2026 (episode ongoing, −8% in Sep 2026)
- [x] `models/yields.py`: new single-line rents (C11) vs clean ready sales, area × type × bedrooms × quarter, zone roll-up with recomputed medians, n ≥ 20 both sides → `ml.agg_yield_quarter` (5,919 cells; 8 outside 2–15%, flagged). Apartments 7.2% / villas 5.2% gross (Q3 2025–Q2 2026)
- [x] `rpt.price_index`, `rpt.yield_quarter` (tag `post_ml`, `make score`) with dbt tests (base = 100, n ≥ min-n, yield ∈ [0, 1], unique keys); pbi_reader reads them (`tests/test_rpt_access.py`)
- [x] `reports/price_index.md`, `reports/yields.md`, 8 figures (`make model-reports`), pointer in `reports/findings.md`; docs/02, 04, 05 (§8 decisions), 06 updated
- [x] Tests: `tests/test_hedonic_index.py` (synthetic market: recovery vs median bias, drifting off-plan premium, min-n, frequency fallback, noise gate, metrics, episodes, DLD alignment; DB checks), `tests/test_yields.py`, config ↔ dbt vars. CI sequence reproduced on a scratch database (fixtures incl. the synthetic DLD index file → `make dbt` → `make train score` → post-build pytest: 48 passed, 1 expected skip)
- [ ] CI green on the pushed commit (owner pushes)

**4a timings** (full data, 16 GB M-series Mac): `make train` ~37 s (index 32 s incl. 18 segments × 14 windows + robustness and validation; yields 4–6 s, all medians in Postgres), `make score` ~3 s, `make model-reports` ~5 s. `make dbt` unchanged apart from the new staging view (10 min 43 s this run, with model runs competing for the database; 7 min 43 s before).

**4b: AVM**
```
Implement features (as-of lag features, no look-ahead, with a pytest proving it), split.py, avm_baseline.py
and avm_lgbm.py per docs/05 §1. Evaluate on the out-of-time test set by segment (MdAPE, ±10/±20% hit rates,
vs baseline), run SHAP, and write reports/avm_model_card.md. Stop and investigate if results look too good
(see CLAUDE.md).
```
**4b status (WIP, 2026-10-01): code, tests and rpt views built; full-data training not yet run to the end.**
- Done: scratch-DB guard (`db.reports_dir` / `figures_dir` / `artifacts_dir`, `tests/test_output_dirs.py`); `hedonic_index` refactor (full re-fit reproduces all 2,432 index points exactly); `features/` (real-time index vintages, as-of comparables, relative target) with the no-look-ahead proof (`tests/test_avm_features.py`); `models/split.py`, `avm.py`, `avm_eval.py`, `avm_explain.py`, `report_avm.py`; `rpt.avm_score`, `rpt.avm_performance`, `rpt.feature_importance` with dbt tests; Makefile, CI, docs/03, docs/06, docs/05 §8. The CI sequence on a scratch DB with the fixtures is green, and no committed report changed. macOS needs `brew install libomp` for LightGBM.
- Untuned probe on full data (test 2025+): LightGBM MdAPE 7.7%, ±10% 60.8%; comparables 9.9% / 49.7%; index-adjusted comparables 10.1%; rolling OLS 12.3%.
- Resume:
  1. `uv run python -m dubai_property.models.avm --trials 20` (saves `artifacts/avm/best_params.json`, reused by later `make train`).
  2. `make score model-reports`, then check the model card's claims against the numbers.
  3. Fill in docs/04 §3 (ml.avm_* rows and counts), the docs/05 §1 "as built" section, this checklist with timings, and a pointer in reports/findings.md; run `make dictionary`.
  4. `make lint test`, then commit.

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
| 0 Setup | ✓ | 2026-09-30 | 2026-09-30 | Scaffold done: `make setup`, `make db` (idempotent), `uv run pytest` (12 passed incl. pbi_reader grant tests) and `dbt debug` pass locally on PG 18.6 / dbt 1.12.5. First push e360d92, CI green |
| 1 Ingestion | ✓ | 2026-09-30 | 2026-09-30 | CI green on 00340f6. Bronze loaded and reconciled (15 files: 1,788,150 transactions, 10,538,926 rent lines, FRED Fed Funds + Brent); re-runs are a no-op. Profiles, `phase1_findings.md` and docs/02 §7 done. Deferred: DLD increment download (stub), EIBOR (manual CBUAE file not yet placed). Open: C11 option and CI sample data (docs/04 §6) |
| 2 dbt | ✓ | 2026-09-30 | 2a, 2b: 2026-09-30 | 2a (silver) done 2026-09-30, CI green on 92b6191: `dbt build` PASS=98 on full data in 4 min 38 s and on the CI fixtures; Phase 1 figures reproduced exactly (reports/dq_report.md §4). 1,267,760 clean market sales, 3,601,613 market-rent lines. All 265 areas zoned. 2b (gold + rpt) done 2026-09-30: `make dbt` 7 min 43 s on full data, 229 dbt nodes pass, gold = silver exactly, `reports/kpi_reconciliation.md` 0 mismatches and the apartment sanity check passes, 10 rpt views (1.77M transaction rows + 392k rent-month cells), data snapshot 2026-09-25. CI green on 5076e27 ([run](https://github.com/SafwanTisekar/dubai-property-analytics/actions/runs/36736326132)) |
| 3 EDA | ✓ | 2026-09-30 | 2026-09-30 | `make eda` runs the three notebooks in ~20 s on full data. Headlines: 211,007 market sales / AED 668.3bn in 2025; Jan–Aug 2026 −19% on 2025 (ready −37%, off-plan −7%), no sign of registration lag; the 2009 spike is a backlog (93.5% of 2009 off-plan registrations applied for earlier); 28–48% of 2025 ready purchases bank-financed (matched lower bound 27.9%); LTV norm 75% → 80%; 2023 apartment prices +1.2% raw vs +14.5% like-for-like. Register totals match DLD's published 2023–25 figures within ~1% on value. Revised the same day after owner review (mortgage KPI, villa area basis, 2026 momentum). `make dbt` 242 nodes pass. CI green on 831502c ([run](https://github.com/SafwanTisekar/dubai-property-analytics/actions/runs/36759956450)). Q9 deferred |
| 4 Models | ◐ | 2026-10-01 | 4a: 2026-10-01 | 4a (hedonic index + yields) done: rolling-window hedonic index from 2011, 18 segments, validates vs DLD at 0.93 / 0.92 / 0.91 (timing-aligned YoY); yields 5,919 cells. Owner decisions 2026-10-01: rolling windows, 2011 start, aligned validation headline (docs/05 §8). 4b, 4c to do |
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
