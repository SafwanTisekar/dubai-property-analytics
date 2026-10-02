# 06 – Power BI Report

## 1. Data connection

- **Source: PostgreSQL** `dubai_property` on the Mac, via Get Data → **PostgreSQL database**, **Import mode** (required for Publish to web). Connection details over the Parallels network are in docs/03 §8.
- Log in as the read-only role **`pbi_reader`**, and select only **`rpt.*` views** (built in Phase 2b: `rpt.transactions`, `rpt.area_month`, `rpt.rent_month`, `rpt.rates_monthly`, `rpt.report_info` and `rpt.dim_date` / `dim_area` / `dim_property_type` / `dim_procedure` / `dim_project`; Phase 4a added `rpt.price_index` and `rpt.yield_quarter`; 4b added `rpt.avm_score`, `rpt.avm_performance`, `rpt.feature_importance`; 4c added `rpt.stress_grid`, `rpt.stress_replay`, `rpt.forecast`, `rpt.forecast_backtest`; Phase 5 added `rpt.dld_price_index`, `rpt.dim_bedrooms`, `rpt.dim_ready_offplan`: 22 views, all imported). Columns have Title Case names (e.g. `"AED Counted Once"`), AED is whole dirhams, and medians are blank where n < 20 (docs/04 §3). All business logic lives in dbt; Power Query only confirms data types.
- Server and database are **Power BI parameters** (`PgServer`, `PgDatabase`), so switching between the Parallels IP and localhost is one change.
- Save as a **Power BI Project (.pbip)** for git, and attach a `.pbix` to GitHub Releases.
- Refresh happens in Desktop (the Mac must be on, with Postgres running), then republish. No gateway is needed because the public report is republished from Desktop rather than refreshed in the Service.
- **Model size budget (Phase 5).** Power BI Pro allows a 1 GB model; Publish to web has no lower limit but slows with model size and query count. Estimate from the measured cardinalities, anchored on Desktop's own cache: the Phase 2b import of the 10 pre-ML tables (transactions included) was a **43.8 MB** `cache.abf`.

  | Table | Rows | Estimate | What drives it |
  |---|---:|---:|---|
  | Transactions | 1,769,938 | ~30–40 MB | AED Counted Once (~400k distinct), Area Sq M (94k), Price per Sq M (57k), Loan (48k) |
  | AVM Score | ~424k | ~6–10 MB | Price AED (~210k distinct), AVM Value AED |
  | Rent Month | 392,190 | ~5–8 MB | four AED / area sums (~190k distinct each) |
  | Area Month | 120,799 | ~2 MB | |
  | everything else | < 40k each | < 2 MB | |
  | **Total** | | **≈ 45–65 MB** | well inside 1 GB; nothing blocks Publish to web |

  Trimmed in Phase 5 rather than in Power Query (column choice is a dbt decision): `rpt.avm_score` keeps only the **out-of-sample** valuations (validation 2024 + test 2025+, ~424k of 904,551: training-period gaps are in-sample and would flatter the chart; owner decision) and drops the comparable-sales value, AVM value per sq m, model and version columns (the baseline comparison is in `rpt.avm_performance`); `rpt.transactions` drops the per-line `"Price AED"` (it repeats a portfolio deal's total on every unit; `"AED Counted Once"` is the value). **Performance risk:** the DAX medians over Transactions (Median Price per Sq M, the raw-median mix-shift line) are the visuals most likely to exceed 1 s on a monthly axis; if Performance Analyzer says so, pre-compute the monthly median in a small rpt view. **To do (owner):** after the first refresh, record the real size from VertiPaq Analyzer (DAX Studio) here.

## 2. Semantic model

Stored as **TMDL** in the PBIP project (`powerbi/DubaiProperty.SemanticModel/definition/`), the source of truth; `tests/test_powerbi_model.py` checks it offline in CI (every rpt view imported once with exactly its columns, every DAX reference resolves, what-if values equal the stress grid's, no hard-coded server).

- **Friendly table names**: Transactions, Area Month, Rent Month, Rates Monthly, Date, Area, Property Type, Procedure, Project, Bedrooms, Ready Off-Plan, Price Index, DLD Price Index, Yield Quarter, AVM Score, AVM Performance, Feature Importance, Stress Grid, Stress Replay, Forecast, Forecast Backtest, Report Info. Columns keep the rpt Title Case names. Partitions read `PostgreSQL.Database(PgServer, PgDatabase)`.
- **Star (connected)**: Transactions, Area Month, Rent Month and AVM Score relate many-to-one, single direction, to **Date** (day grain, marked as the date table), **Area**, **Property Type**, **Bedrooms** and **Ready Off-Plan** (Rent Month: no Ready / Off-Plan, rents are of ready units); Rates Monthly → Date; Transactions and AVM Score → Project; Transactions → Procedure. One synced slicer panel therefore filters every fact. Relationship autodetect is off.
- **Model outputs are disconnected** (Price Index, DLD Price Index, Yield Quarter, Stress Grid / Replay, Forecast / Backtest, AVM Performance, Feature Importance, Report Info) and measures bridge them with `TREATAS`: dates onto `Period Start` / `Quarter Start`, `'Area'[Zone]` / `[Area Key]`, property type and bedrooms onto their columns. **Why:** those tables mix grains (Dubai, type, zone and area rows, with NULL area keys on the Dubai and zone rows), so a physical relationship to Area would make any area slicer silently drop the Dubai and zone rows a card needs.
- **What-if and selector tables** (DAX calculated tables, integer keys so equality with `rpt.stress_grid` is exact): `Price Shock %` (0 to −50, step 5); `LTV %` with **50, 60, 70, 80, 85** only (85 labelled "UAE national first home cap (worst case)"; Phase 4c, owner 2026-10-01); `Replay Depth` (Dubai-wide = lower range / own series = upper range); `Forecast Scenario` (Rates flat / +100bp / −100bp).
- **Display folders**: Market, Financing, Prices, Yields, Valuation, Risk (with `Risk\Concentration`, `Risk\Outlook`), Rates, and **Report** (header, footer, dynamic insight titles; added in Phase 5). Every measure has a description. `discourageImplicitMeasures` is on: visuals use measures, not dragged columns.
- **Report (PBIR)**: the six pages are PBIR JSON (`DubaiProperty.Report/definition/pages/`), the theme (`powerbi/theme.json`) is registered in the PBIP so it applies on open, and `tests/test_powerbi_model.py` validates every report file against the official Microsoft schemas (vendored in `powerbi/schemas/pbir/`, MIT), every field against the model, and every formatting property and value against an index of Microsoft's report theme schema (`powerbi/schemas/visual_objects.json`).
- **Format**: every AED amount is `"AED "#,0`; cards and axes show bn / M through the visual's **display units** (set explicitly to Billions or Millions with 1 decimal: Auto switches to Trillions on all-time totals). Excel-style scaling commas (`#,0.0,,,"bn"`) are **not** used: Power BI rendered them literally ("AED 3.6,,,Tbn", Phase 5 gate), and `tests/test_powerbi_model.py` rejects them. Percentages `0.0%` (MdAPE `0.00%`); changes `+0.0%;-0.0%`; index `0.0`.

## 3. Measures

All measures live in the measure table **`_Measures`** (`tables/_Measures.tmdl`); `powerbi/measures.dax` is a read-only review copy (`make pbi-measures`; a test fails if it is stale). They only aggregate rpt views: definitions sit in dbt. `reports/kpi_reconciliation.md` §7 lists the value every card must show.

| Folder | Measures | Notes |
|---|---|---|
| Market | Market Sales, Market Sales Value (+ PY, YoY %), Clean Sales, Median Price per Sq M, Area-Weighted Price per Sq M (Homes), Off-Plan Sales, Off-Plan Share (Count / Value) | Counts and AED from Area Month (reconciled to Transactions); medians on Transactions, blank under min-n |
| Financing | Ready Market Sales, Purchase Mortgages, **Purchase Mortgage Share** (headline, lower bound), Ready Sales Not Bank-Financed, New Mortgages (per 100 Sales), New Mortgage Loans, Portfolio Mortgage Deals / Value, Median Purchase LTV | docs/01 §4 definitions |
| Rates | Fed Funds Rate, EIBOR 3M, Reference Rate (EIBOR, else Fed Funds), Reference Rate Label | EIBOR is not loaded yet, so charts show Fed Funds labelled as the proxy |
| Prices | Index Value, Index YoY / Value (Latest Complete) / Drawdown from Peak (cards: latest non-partial period in the selection), Index Drawdown, Max Drawdown, DLD Index Value, Index Value (Apartments), Raw Median Price per Sq M (Apartments), Raw Median Rebased | Segment from a slicer on `'Price Index'[Segment]` (Dubai when none) |
| Yields | Gross Yield (Latest 4 Quarters) (sales-weighted zone cells, as reports/yields.md), Gross Yield by Area, Gross Yield by Quarter, Index Growth 3Y (Zone), New Market Rents, Area-Weighted New Rent per Sq M (Homes), New Rent per Sq M | Min-n applied upstream (both sides) |
| Valuation | AVM Test MdAPE / Hit Rate 10% / 20% (+ Baseline), MdAPE Gain vs Baseline, AVM Segment MdAPE, Valued Sales, AVM MdAPE / Hit Rate (Interactive), Median Sale Price / AVM Value / Gap %, Flagged for Review / Share, Mean Abs SHAP | Headline cards read AVM Performance (model card); interactive ones recompute on out-of-sample rows |
| Risk | Selected Shock / LTV / Stress Segment / Ready / Off-Plan, Negative Equity Share / AED / Count, Stress Purchases, Negative Equity Share (CBUAE Cap / Registered Loans), Replay Negative Equity Share, Negative Equity Share by Area | Shares are read per segment row, never re-averaged; blank under min-n |
| Risk\Concentration | Off-Plan Market Sales (Lines), Master Project Share, Top 10 Master Project Share, Master Project HHI | **Proxy** for developer concentration (Q9 needs the DLD projects file) |
| Risk\Outlook | Forecast Actual / Central / Lower-Upper 80 / 95, Forecast 12M Change / Lower / Upper, Band label | Scenario from `Forecast Scenario` |
| Report | Min N, Data As Of Label, Footer Attribution, Selected Year Label, Stress Disclaimer, Title * (dynamic insight titles) | |

Every stress visual carries "Illustrative, not a regulatory stress test" (`[Stress Disclaimer]`). The historical replay rows have no Shock Pct; the two depths ("Replay: 2014-2020, Dubai-wide", the lower range, and "…, own series", the upper range) are chosen with `Replay Depth`. `tests/test_kpi_reconciliation.py` reproduces every docs/01 §4 KPI in SQL; the cards must match §7 of its report before publishing.

## 4. Report pages

16:9 canvas, a consistent header (title, "Source: Dubai Land Department (CC BY 4.0)", data-as-of date), a synced slicer panel (Year, Zone/Area, Property sub-type, Bedrooms, Off-plan/Ready) and one theme.

| # | Page | Answers | Visuals |
|---|---|---|---|
| 1 | **Executive Overview** | Q1 | KPI cards (Sales Value, Sales Count, Median AED/sq m, Index YoY, Purchase Mortgage Share, Off-plan Share) · sales value by month with **cycle annotations** (2008, 2014, 2020, 2021+) · top 10 areas by value · 3 insight text boxes |
| 2 | **Financing & Market Mix** | Q2 | Ready sales: bank-financed (matched purchase mortgage) vs not bank-financed at registration, by month · purchase-mortgage share and EIBOR 3M as stacked panels on one time axis (no dual axis) · new mortgages per 100 sales · off-plan vs ready share over time · off-plan share by area bar |
| 3 | **Prices & Index** | Q3, Q6 | Hedonic index lines (Dubai / apartments / villas / zones) vs DLD official index · **raw median vs hedonic** (mix-shift story) · AED/sq m by area map · bedrooms × zone matrix · drawdown chart |
| 4 | **Rental Yields** | Q4 | Yield by area map · yield vs 3-year growth scatter (bubble = sales volume; quadrant lines) · yield trend by zone · rent per sq m by bedrooms |
| 5 | **Valuation Model (AVM)** | Q5 | AVM KPI cards (MdAPE, ±10%/±20% hit rates vs baseline) · accuracy by segment bar · top feature importance · actual vs predicted by month · table of the largest AVM gaps by area/project |
| 6 | **Risk & Stress Test** | Q6, Q7, Q9 | **Price Shock** and **LTV** sliders → Negative Equity Share and AED cards · negative-equity share by area map/bar · historical drawdown replay · developer concentration (HHI, top developers' off-plan share) · 12-month outlook fan chart |

**Maps: none in v1 (owner decision, 2026-10-02).** The Azure Maps visual must be enabled by a tenant admin, which the owner's account isn't, and Bing maps are being retired. Every geographic view is therefore a **bar chart by zone or area, top N, sorted by the same measure** (pages 3, 4, 6; `powerbi/BUILD.md`). The OpenStreetMap centroids stay in `'Area'[Latitude]` / `[Longitude]` (`reports/area_centroids.md`: 194 of 265 areas, 97.7% of 2023+ market sales) and the footer keeps the ODbL credit, so a map can be added later without model changes. **No Python/R visuals**; SHAP images go on the website.

**Phase 5 substitutions** (data not available, decisions 2026-10-01): page 2 shows the **Fed Funds rate as the EIBOR proxy** (labelled; EIBOR swaps in once a CBUAE file is loaded); page 6's developer concentration is a **master-project proxy** (top-10 master projects' share of off-plan market sales and an HHI over master projects, labelled as a proxy; owner decision) until the DLD projects file brings developer names.

## 5. Design standards

- Insight titles, e.g. "Off-plan now drives X% of sales value, up from Y% in 2019", rather than plain labels.
- 6–8 visuals per page maximum, aligned grid, alt text on every visual.
- AED everywhere. Use Dubai-appropriate naming (communities, not "neighbourhoods").
- Performance Analyzer: under 1 s per visual.

## 6. Publishing

The mechanics are the same as any Publish-to-web report: a work/school account, a Power BI Pro (trial) licence and the tenant setting enabled (see docs/03 §8–9).
1. Publish to My workspace → File → Embed report → **Publish to web (public)**.
2. Put the embed URL in `website/config.js` and record it, with the licence expiry date, in docs/08.
3. Monthly refresh: `make update` → refresh in Desktop → republish (the embed URL stays the same). This is a nice "living dashboard" talking point.
4. Everything in the model becomes public. That's fine for DLD open data under CC BY 4.0, with attribution shown.
