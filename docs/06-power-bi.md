# 06. Power BI report

The semantic model, measures, report pages, design rules and publishing of the Power BI report. Visual-by-visual detail: `powerbi/VISUALS.md`; build rules: `powerbi/BUILD.md`.

## 1. Data connection and size

- **Source:** PostgreSQL `dubai_property`, **import mode** (required for Publish to web), as the read-only role `pbi_reader`, over the Parallels network (docs/03 §8). Server and database are the parameters `PgServer` / `PgDatabase`.
- **Only `rpt.*` views, 22 in all:** `transactions`, `area_month`, `rent_month`, `rates_monthly`, `report_info`, the dimensions (`dim_date`, `dim_area`, `dim_property_type`, `dim_procedure`, `dim_project`, `dim_bedrooms`, `dim_ready_offplan`), the model outputs (`price_index`, `dld_price_index`, `yield_quarter`, `avm_score`, `avm_performance`, `feature_importance`, `stress_grid`, `stress_replay`, `forecast`, `forecast_backtest`). Title Case column names, AED in whole dirhams, medians blank where n < 20 (docs/04 §3). Business logic lives in dbt; Power Query only sets types.
- **Refresh:** in Desktop with the Mac and Postgres running, then republish. No gateway: the public report is republished, not refreshed in the Service.
- **Size budget.** Pro allows a 1 GB model; Publish to web slows with model size. Estimate, anchored on the 43.8 MB `cache.abf` of the first 10-table import:

  | Table | Rows | Estimate | What drives it |
  |---|---:|---:|---|
  | Transactions | 1,769,938 | ~30–40 MB | AED Counted Once (~400k distinct), Area Sq M (94k), Price per Sq M (57k), Loan (48k) |
  | AVM Score | ~424k | ~6–10 MB | Price AED (~210k distinct), AVM Value AED |
  | Rent Month | 392,190 | ~5–8 MB | four AED / area sums (~190k distinct each) |
  | Area Month | 120,799 | ~2 MB | |
  | everything else | < 40k each | < 2 MB | |
  | **Total** | | **≈ 45–65 MB** | well inside 1 GB |

  Trimmed in dbt rather than Power Query: `rpt.avm_score` keeps only the **out-of-sample** valuations (validation 2024 + test 2025+, ~424k of 904,551) and four columns; `rpt.transactions` drops the per-line `"Price AED"` (it repeats a portfolio deal's total on every unit; `"AED Counted Once"` is the value). The real size from VertiPaq Analyzer is still to be recorded (docs/08).

## 2. Semantic model

Stored as **TMDL** in `powerbi/DubaiProperty.SemanticModel/definition/`, the source of truth. `tests/test_powerbi_model.py` checks it offline in CI: every rpt view imported once with exactly its columns, every DAX reference resolves, what-if values equal the stress grid's, no hard-coded server.

- **Tables:** Transactions, Area Month, Rent Month, Rates Monthly, Date, Area, Property Type, Procedure, Project, Bedrooms, Ready Off-Plan, Price Index, DLD Price Index, Yield Quarter, AVM Score, AVM Performance, Feature Importance, Stress Grid, Stress Replay, Forecast, Forecast Backtest, Report Info. Columns keep the rpt names.
- **Star:** Transactions, Area Month, Rent Month and AVM Score relate many-to-one, single direction, to **Date** (marked date table), **Area**, **Property Type**, **Bedrooms** and **Ready Off-Plan** (not Rent Month: rents are of ready units); Rates Monthly → Date; Transactions and AVM Score → Project; Transactions → Procedure. One synced slicer panel filters every fact. Autodetect is off.
- **Model outputs are disconnected** and measures bridge them with `TREATAS` (dates, zone, area key, type, bedrooms). Those tables mix grains (Dubai, type, zone and area rows, with NULL area keys on Dubai and zone rows), so a physical relationship to Area would let an area slicer silently drop the rows a card needs.
- **What-if and selector tables** (integer keys, so equality with `rpt.stress_grid` is exact): `Price Shock %` (0 to −50, step 5); `LTV %` with 50, 60, 70, 80, 85 only; `Replay Depth` (Dubai-wide / own series); `Forecast Scenario` (rates flat / +100bp / −100bp).
- **Report (PBIR):** pages, bookmarks and theme are PBIR JSON in `DubaiProperty.Report/definition/`, validated against the official Microsoft schemas (vendored in `powerbi/schemas/`, MIT), every field against the model, and every formatting property against an index of the theme schema.
- **Formats:** AED `"AED "#,0`, with bn / M via display units set explicitly (Auto switches to trillions on all-time totals); percentages `0.0%` (MdAPE `0.00%`); changes `+0.0%;-0.0%`; index `0.0`. Excel-style scaling commas are rejected by a test: Power BI renders them literally.

## 3. Measures

All measures live in `_Measures` (`tables/_Measures.tmdl`); `powerbi/measures.dax` is a read-only review copy (`make pbi-measures`; a test fails if it is stale). Measures only aggregate rpt views; every card value is listed in `reports/kpi_reconciliation.md` §7.

| Folder | Measures | Notes |
|---|---|---|
| Market | Market Sales, Market Sales Value (+ PY, YoY %), Clean Sales, Median Price per Sq M, Area-Weighted Price per Sq M (Homes), Off-Plan Sales, Off-Plan Share (Count / Value) | Counts and AED from Area Month (reconciled to Transactions); medians on Transactions, blank under min-n |
| Financing | Ready Market Sales, Purchase Mortgages, **Purchase Mortgage Share** (headline, lower bound), Ready Sales Not Bank-Financed, New Mortgages (per 100 Sales), New Mortgage Loans, Portfolio Mortgage Deals / Value, Median Purchase LTV | docs/01 §4 definitions |
| Rates | Fed Funds Rate, EIBOR 3M, Reference Rate (EIBOR, else Fed Funds), Reference Rate Label | Fed Funds labelled as the proxy until EIBOR is loaded |
| Prices | Index Value, Index YoY / Value (Latest Complete) / Drawdown from Peak, Index Drawdown, Max Drawdown, DLD Index Value, Raw Median Price per Sq M (Apartments), Raw Median Rebased | Segment from a slicer on `'Price Index'[Segment]` (Dubai when none) |
| Yields | Gross Yield (Latest 4 Quarters), Gross Yield by Area / by Quarter, Index Growth 3Y (Zone), New Market Rents, Area-Weighted New Rent per Sq M (Homes), New Rent per Sq M | Min-n applied upstream on both sides |
| Valuation | AVM Test MdAPE / Hit Rate 10% / 20% (+ Baseline), MdAPE Gain vs Baseline, AVM Segment MdAPE, Valued Sales, interactive MdAPE / hit rates, Median Sale Price / AVM Value / Gap %, Flagged for Review / Share, Mean Abs SHAP | Headline cards read AVM Performance (the model card); interactive ones recompute on out-of-sample rows |
| Risk | Selected Shock / LTV / Segment, Negative Equity Share / AED / Count, Stress Purchases, Negative Equity Share (CBUAE Cap / Registered Loans), Replay Negative Equity Share, by Area | Shares read per segment row, never re-averaged; blank under min-n |
| Risk\Concentration | Off-Plan Market Sales (Lines), Master Project Share, Top 10 Master Project Share, Master Project HHI | **Proxy** for developer concentration |
| Risk\Outlook | Forecast Actual / Central / Lower-Upper 80 / 95, Forecast 12M Change / Lower / Upper | Scenario from `Forecast Scenario` |
| Report | Min N, Data As Of Label, Footer Attribution, Selected Year Label, Stress Disclaimer, dynamic insight titles | |

Every stress visual carries "Illustrative, not a regulatory stress test". `tests/test_kpi_reconciliation.py` reproduces every docs/01 §4 KPI in SQL.

## 4. Report pages

16:9 canvas; a navy side bar with the page navigator; a header with title, data-as-of date, Reset all filters and a link to the KPI guide; a synced slicer panel (Year, Zone / Area, Property type, Bedrooms, Ready / Off-plan); the attribution footer on every page.

| # | Page | Answers | Main visuals |
|---|---|---|---|
| | Introduction, Key terms and methods | | What the report is for, how to read it, the four models in plain words |
| 1 | **Executive overview** | Q1 | KPI tiles (sales value, count, median AED / sq m, like-for-like YoY, off-plan share, mortgage share); sales value by month with cycle annotations; top areas by value; three insight texts |
| 2 | **Financing** | Q2 | Ready sales bank-financed vs not; purchase-mortgage share and the rate on one time axis (stacked, no dual axis); new mortgages per 100 sales; off-plan share over time and by area |
| 3 | **Prices** | Q3, Q6 | Hedonic index vs DLD's; raw median vs like-for-like (mix shift); AED / sq m by area; bedrooms × zone matrix; drawdown |
| 4 | **Rental yields** | Q4 | Yield by area; yield vs 3-year growth; yield by zone over time; rent per sq m by bedrooms |
| 5 | **Valuation model** | Q5 | MdAPE and hit rates vs the baseline; accuracy by segment (same sales); feature importance; actual vs predicted by month; largest gaps |
| 6 | **Risk and stress test** | Q6–Q9 | Shock and LTV slicers → negative-equity share and AED; by area; 2014→2020 replay; master-project concentration; 12-month outlook fan |
| | KPI guide | | Every KPI's meaning, calculation and source, generated from the measure descriptions |

**No maps in v1** (decision 2026-10-02): the Azure Maps visual must be enabled by a tenant admin and Bing maps are being retired, so every geographic view is a bar chart by zone or area, top N. The OpenStreetMap centroids stay in `'Area'[Latitude]` / `[Longitude]` (194 of 265 areas, 97.7% of 2023+ market sales) and the footer keeps the ODbL credit, so a map can be added without model changes. No Python/R visuals.

**Substitutions** (data not loaded, 2026-10-01): page 2 shows Fed Funds as the EIBOR proxy, labelled; page 6's developer concentration is a master-project proxy, labelled.

## 5. Design standards

- Insight titles that state the finding, not plain labels.
- 6–8 visuals per page, aligned grid, alt text on every visual.
- AED everywhere; communities, not "neighbourhoods".
- Built-in visuals only (custom visuals watermark without a licence and the report is public).
- Target under 1 s per visual in Performance Analyzer.

## 6. Publishing

1. Publish to My workspace → File → Embed report → **Publish to web (public)** (licensing: docs/03 §9).
2. The embed URL is recorded in the docs/08 Publishing record and set in the site repository's `config.js`; a test checks they match.
3. Monthly refresh: rebuild → refresh in Desktop → republish. The embed URL stays the same.
4. Everything in the model becomes public, which is fine for DLD open data under CC BY 4.0 with attribution.

## 7. Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-01 | Semantic model hand-written as TMDL; model outputs disconnected and bridged with TREATAS | §2. Their Dubai / zone rows have NULL area keys, so a relationship would let an area slicer drop them |
| 2026-10-02 | AED formats are `"AED "#,0` only; bn / M via display units; thousands via a measure formatted `"AED "#,0"K"` | Scaling commas (`#,0.0,,,"bn"`) render literally in Power BI ("AED 3.6,,,Tbn", gate 0) |
| 2026-10-02 | No maps in v1: bar charts by area, top N | Azure Maps needs a tenant admin; centroids kept for later |
| 2026-10-02 | Report pages built as PBIR JSON and validated offline (official schemas, model fields, theme-schema formatting index, query expressions); `powerbi/VISUALS.md` generated from them | Reproducible, reviewable report definition; Desktop remains the final check (manual review gates) |
| 2026-10-02 | Render rules: charts ≥ 240 × 180 px, top-N bars ≥ 24 px each, subtitles only under a title, card formatting on `$id = default` | Final gate: tiny panels drew a placeholder icon, bar charts scrolled, subtitles and label settings were silently ignored |
| 2026-10-02 | Model-output rpt views keep ratios at 6 decimals (`rpt_ratio` macro) | Power BI rounds half up: 0.650478 stored as 0.6505 showed 65.1% against the model card's 65.0% |
| 2026-10-02 | Yield aggregates leave out cells outside the 2–15% sanity band | Two flagged Al Barsha cells drove a 14.1% zone yield; apartments 7.2% → 7.1% (docs/05 §8) |
| 2026-10-02 | AVM features shown with readable names (`seed_avm_feature_label`, tested to cover every feature) | "proj_rel_12m" means nothing to a reader; "Project price level (12m)" does |
| 2026-10-02 | AVM segment chart compares the models on the same sales (breakdowns "… (same sales)" in `rpt.avm_performance`) | Own coverage put LightGBM's villas at 8.91% (21,810) beside the model card's 8.66% head-to-head (20,527) |
| 2026-10-02 | Redesign: navy side bar with a built-in page navigator, grey rounded content panel, header bar (title, Data as of, Reset all filters, ⓘ to the KPI guide), white rounded cards with section headings, KPI tiles with a split strip, navy / magenta palette | Restyled to a reference screenshot (style only). Built-in visuals only: custom visuals watermark without a licence and the report is public |
| 2026-10-02 | "Reset all filters" opens a per-page bookmark (data only, the page's slicers only) restoring the defaults (Year 2025, page 6 Dubai / −20 / 80%, Accuracy by same sales) | The first version (Clear all slicers) left the single-select Year slicer on its value (gate 2); bookmarks are generated from the slicers' defaults and schema-validated |
| 2026-10-02 | Short zone labels (`seed_zone_label`, `'Area'[Zone Short]`) for narrow columns | The page 3 matrix scrolled sideways with full zone names |
| 2026-10-02 | Two beginner pages (Introduction, Key terms & methods) before page 1, numbers from measures | A non-specialist should understand the report in a minute per page; typed numbers would go stale at the next refresh |
| 2026-10-02 | Dynamic sentences (measures) are shown in one-column tables, not cards | Card visuals cut measure text to one line (gate 1); a table wraps it at a fixed column width, with the header as the card heading |
| 2026-10-02 | KPI guide page generated from the measure descriptions (`'KPI Guide'` calculated table) | One source of truth for what a KPI means; a test fails if a tile measure lacks meaning, calculation or source |
| 2026-10-02 | Page 6 keeps stress segment, shock and LTV controls only (replay depth, scenario and outlook segment shown in strips) | All controls fit one row; the defaults are the published headline figures |
| 2026-10-02 | Card and top-N sizes assume Desktop's rendered sizes (≈ 1.73 px per point, ≈ 24 px per bar, 32 px per table row), not the nominal PBIR ones | Gate 3: files passed nominal checks yet grouped cards and bar charts clipped on screen |
