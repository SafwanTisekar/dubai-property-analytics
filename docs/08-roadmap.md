# 08. Roadmap and changelog

What was built in each phase, the key results and decisions, what is still open, and the publishing record. Detailed decision logs live in docs/01, 04, 05, 06 and 07.

## Status

| Phase | Status | Dates | Summary |
|---|---|---|---|
| 0 Setup | Done | 2026-09-29 → 09-30 | Repository scaffold, Postgres, roles and schemas, CI; Power BI licensing and Publish to web tested |
| 1 Ingestion | Done | 2026-09-30 | 15 files loaded to bronze with COPY and reconciled; profiles and the four Phase 1 investigations |
| 2 dbt | Done | 2026-09-30 | Silver (rules C1–C22), gold star schema, 10 rpt views; reconciliation exact; `make dbt` 7 min 43 s |
| 3 EDA | Done | 2026-09-30 | Three notebooks over SQL functions; findings Q1–Q4; mortgage KPI redefined after review |
| 4 Models | Done | 2026-10-01 | Hedonic index, yields, AVM, stress test, forecast; model cards and reports |
| 5 Power BI | Done | 2026-10-01 → 10-02 | TMDL model, nine PBIR pages, redesign, published to the web |
| 6 Website | In progress | 2026-10-02 → | Site in its own repository, numbers from the database; deploy and Lighthouse pending |
| 7 Launch | Open | | README, release, final review |

## Phase 0: Setup

- Repository scaffold: uv project (Python 3.11), Makefile, pre-commit with ruff, `config.py`, `db.py` (psycopg 3, SQLAlchemy, connectorx), dbt-postgres project with `dbt_utils` and `dbt_expectations`, GitHub Actions with a `postgres:18` service.
- `make db`: UTF-8 database `dubai_property` (C collation), roles `dpa_owner` and `pbi_reader`, schemas bronze / silver / gold / ml / rpt; `pbi_reader` gets SELECT on rpt only, including default privileges. Idempotent.
- PostgreSQL 18.6 via Homebrew; Power BI Desktop in a Windows 11 VM under Parallels (docs/03 §8).
- Power BI: work account on my own domain, admin takeover via DNS TXT, Publish to web enabled, Pro trial started 2026-09-29; a throwaway report rendered in a private window (docs/03 §9).
- DLD bulk files downloaded by hand: transactions (2 files, 1,788,150 rows) and rents (11 files, ~10.5M lines). Projects, buildings, units and lookups deferred.

## Phase 1: Ingestion, bronze and profiling

- `load_bronze.py`: every CSV → `bronze.*` as `text` via `COPY`, BOM- and encoding-safe, metadata columns, a transactional load manifest so re-runs skip loaded files, and a parser record count that must equal the COPY count (docs/04 §1).
- `download_rates.py`: FRED Fed Funds and Brent. EIBOR is a manual CBUAE download, not yet placed.
- Profiles (`reports/profile_*.md`), `reports/bronze_reconciliation.md` (15/15 files match), docs/02 §7 filled in.
- Investigations in `reports/phase1_findings.md`: procedure values, `actual_worth` on mortgage rows (it is the loan amount on completed-property mortgages, median loan / price 0.795), multi-line rent contracts (full amount repeated on every line, 5.24× inflation), date formats; portfolio double counting quantified (+AED 130.9bn on a naive mortgage sum).
- `max_wal_size` raised to 4 GB after checkpoint pressure slowed the rent load (docs/03 §7).

## Phase 2: dbt silver and gold

**2a, silver.** Seeds (procedure map with 58 pairs, rooms, rent sub-types, 265 areas all zoned), staging and intermediate models with rules C1–C22 as flags (docs/04 §2), `reports/dq_report.md` (rows per step and per rule, population waterfalls), committed CI fixtures (`make fixtures`, ~2k real lines per table). Every Phase 1 count and AED total is reproduced exactly on full data.

**2b, gold and rpt.** Conformed `dim_property_type` (usage group × class, 66 rows), `dim_date`, `dim_area`, `dim_procedure`, `dim_project`; facts `fct_transaction` (with `aed_counted_once`), `fct_rent_contract` (allocated rent), `fct_rates_monthly`; additive aggregates `agg_area_month`, `agg_rent_month`; 10 rpt views (Title Case, whole-dirham AED, medians blank under min-n). Tests: keys and relationships, gold = silver, aggregates = facts, and `reports/kpi_reconciliation.md` (0 mismatches). `seed_ltv_rules` verified against the CBUAE rulebook and dated. `docs/data-dictionary.md` generated.

Changes after review: per-class rent area caps (C21, 85,298 lines), the data snapshot date (2026-09-25) ends the reporting scope (C18, 24,223 rent lines start after it), and the area-weighted headline covers residential apartments and villas only.

**Timings and rpt row counts** (full data, 16 GB M-series Mac, 4 dbt threads): `make dbt` 7 min 43 s, of which `dbt build` 6 min 37 s for 10 seeds, 16 tables, 13 views and 190 tests (`fct_rent_contract` ~50 s, `fct_transaction` ~12 s).

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

## Phase 3: Exploratory analysis

- `src/dubai_property/analysis/`: every function aggregates in SQL over gold / rpt and returns a small frame; the three notebooks only call these functions and plot (`make eda`, ~20 s).
- 16 charts in one style (colour-blind-safe palette, 2026 marked partial, DLD attribution).
- `reports/findings.md`: 211,007 market sales worth AED 668.3bn in 2025; Jan–Aug 2026 −19% on 2025 (ready −37%, off-plan −7%); the 2009 spike is a registration backlog; 28–48% of 2025 ready purchases bank-financed; LTV norm 75% → 80% from April 2020; 2023 apartment prices +1.2% raw vs +14.5% like for like. Register totals match DLD's published 2023–25 figures within ~1% on value.
- Revised after review: the mortgage KPI became the purchase-mortgage share of ready sales (docs/04 Decisions), the villa vs apartment price comparison was withdrawn (villa areas mix plot and built-up sizes), and a 2026 momentum check with registration-lag tests was added.
- Q9 (developer concentration) deferred: it needs developer names from the DLD projects file.

## Phase 4: Models

**4a, hedonic index and yields.** DLD's Residential Sale Index loaded as the benchmark (data ends May 2024). Rolling-window hedonic index from January 2011, 18 segments, Jan 2019 = 100; validates against DLD at r = 0.93 / 0.92 / 0.91 (timing-aligned YoY). The pooled-fit robustness check was material (off-plan premium +6% → +38%), which decided the rolling-window method. Yields: 5,919 area and zone cells with n ≥ 20 on both sides; apartments 7.1%, villas 5.2% gross. `make train` ~37 s.

**4b, AVM.** Real-time index vintages and as-of features with a no-look-ahead test; out-of-time split; comparables, index-adjusted comparables, rolling hedonic OLS and LightGBM. Test MdAPE **6.8%**, ±10% **65.0%**, ±20% **88.2%** vs comparables 9.9% / 50.3% / 76.1%; no leakage alarm. Honest negatives reported: index-adjusted comparables lose to plain ones, comparables edge LightGBM on villa MdAPE, and Optuna results were flat. 904,551 sales scored. `make train` AVM step ~33 min (≈12 min with the committed tuned parameters).

**4c, stress test and forecast.** 459,644 recent sales marked to market; at 80% LTV a 20% fall puts 22% of recent ready apartment buyers in negative equity; the 2014→2020 replay gives 43% to 80%. SARIMAX beats naive on the index (11 of 12 cells) but not on volume (1 of 12); central path +4.6% to Aug 2027. Two bugs found in review and fixed with tests (an accelerating drift term, a double log in the volume backtest).

**Incident (2026-10-01).** A fixture run meant for a scratch database reset the main database's bronze, because the Makefile's `-include .env` overrode the environment variable. The database was rebuilt from `data/raw`; the AVM was re-tuned (test MdAPE 6.83% vs 6.82%, so the result is stable) and its parameters committed. The loader now refuses non-`data/raw` roots and un-flagged resets on the main database (docs/05 §8).

## Phase 5: Power BI

- rpt extended to 22 views (DLD index rebased, bedroom and ready / off-plan slicer dimensions, map attribution); `rpt.avm_score` trimmed to out-of-sample rows for size.
- Area centroids from OpenStreetMap Nominatim: 194 of 265 areas, 97.7% of 2023+ market sales.
- Semantic model hand-written as TMDL: 22 tables, 23 relationships, model outputs bridged with `TREATAS`, integer what-if tables, all measures with descriptions; validated offline in CI (`tests/test_powerbi_model.py`).
- Report pages built as PBIR JSON and validated against the official schemas, then reviewed in Desktop through several gates: Introduction, Key terms, six report pages and a KPI guide generated from the measure descriptions; per-page reset bookmarks; single-select Year slicer showing only years with data.
- Redesign (5b): navy side bar with page navigator, header bar, white cards, navy / magenta palette.
- No maps in v1: Azure Maps needs a tenant admin, so geographic views are top-N bar charts.
- Published to the web on 2026-10-02.

## Phase 6: Website

- Personal site with this project on its own page, moved to its own repository `SafwanTisekar.github.io` (docs/07). `make site` writes every number from the database into the pages and `data/site.json`; `make site-shots` turns a Desktop PDF export into page screenshots.
- Embed loads lazily with a fallback on timeout, licence end date or no JavaScript.
- Tests in both repositories (numbers, links, images, contrast, attribution, no contact details).

## Phase 7: Launch

- [x] README with the architecture diagram, report screenshot, findings and how to run
- [x] Repository cleanup: licence, `.gitattributes`, documentation tightened
- [ ] v1.0 release with the PBIX
- [ ] Monthly refresh routine

## Open items

- [ ] EIBOR: place the CBUAE history in `data/raw/cbuae/` and run `make bronze`; Fed Funds stands in until then.
- [ ] DLD projects file: developer names (Q9 developer HHI, property age for the AVM).
- [ ] Every Power BI card checked against `reports/kpi_reconciliation.md` §7; Performance Analyzer timings; model size from VertiPaq Analyzer (docs/06 §1).
- [ ] Reset all filters confirmed in the Service after republishing.
- [ ] 71 areas without a centroid (`centroid_source = manual` in `seed_area.csv`), if a map is added.
- [ ] Site: first deploy (Settings > Pages > Source: GitHub Actions) and Lighthouse ≥ 90.
- [ ] Renew Power BI Pro or buy a licence before the trial ends (~2026-11-27).
- [ ] `make update` (incremental monthly refresh) is a stub.

## Publishing record

| Publishing record | Value |
|---|---|
| Power BI tenant/account | Own-domain tenant, Global Admin via DNS TXT admin takeover; **Publish to web** enabled in the tenant settings |
| Publish-to-web URL | https://app.fabric.microsoft.com/view?r=eyJrIjoiYzgxYTFiNGEtNTQ1OC00YWExLTk2YTctY2E2MDMwNjQyNjY5IiwidCI6ImQ0M2RmOTBjLTEwYTctNDg5MC1hYjBjLWU5YWMwNDQ2NjRiNCJ9 |
| Published on | 2026-10-02 |
| Licence/trial expires | Pro trial started 2026-09-29, ends **~2026-11-27**. The embed stops working if the licence lapses |
| Website URL | https://safwantisekar.github.io/ (project page: /projects/dubai-property/) |
| Data as of | 2026-09-25 (snapshot) |
