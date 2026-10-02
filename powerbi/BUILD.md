# Building the report in Power BI Desktop

A step-by-step guide to the six pages of docs/06 §4 on the semantic model in `DubaiProperty.SemanticModel` (Phase 5). Every field below exists in the model; every number a card shows is listed, with its filters, in **`reports/kpi_reconciliation.md` §7** (the card checklist). Measures are in the `_Measures` table, in display folders by page topic (docs/06 §3); `powerbi/measures.dax` is a readable copy.

## 0. Setup (once)

1. **No maps in v1** (owner decision, 2026-10-02): the Azure Maps visual needs a tenant admin to enable it, so every geographic view is a **bar chart by zone or area, top N, sorted by the same measure**. `'Area'[Latitude]` / `[Longitude]` stay in the model (OpenStreetMap centroids) for a map later. **Publish to web** is already on (docs/03 §9).
2. Close Desktop. On the Mac: start Parallels, then `make pbi-ready` (docs/03 §8).
3. If the model changed since the last open, delete `powerbi/DubaiProperty.SemanticModel/.pbi/cache.abf` (stale imported data; gitignored, rebuilt by the refresh).
4. Open `powerbi/DubaiProperty.pbip` → **Refresh**. Parameters (Transform data → Manage parameters): `PgServer` = `10.211.55.2:5432`, `PgDatabase` = `dubai_property`.
5. **The theme is registered in the PBIP** (`StaticResources/RegisteredResources/DubaiPropertyAnalytics.json`, referenced from `report.json`), so it applies on open: no manual import. The source is `powerbi/theme.json`; after editing it, copy it over the registered file (a test fails if they differ). The palette is the one the figures and the website use: blue = ready / apartments, orange = off-plan / villas, aqua = a third series, in that fixed order (colour follows the entity, never the rank). Text is `#0b0b0b` (19.2:1 on the background) and `#52514e` (7.7:1) for axis labels and subtitles; `#8a8984` is for gridlines only. Aqua, yellow and magenta are under 3:1 on the background, so **any visual that shows them also shows data labels or a legend**.
6. Canvas: every page is 16:9, **1280 × 720** (already set on the six empty pages).
7. **Money formats.** Every AED measure is formatted `"AED "#,0`. For bn / M, set the visual's **display units explicitly** (Billions or Millions, 1 decimal): *Auto* switches to Trillions on all-time totals (the Phase 5 gate showed "AED 3.6…T"). Never type Excel-style scaling commas (`#,0.0,,,"bn"`) into a format string: Power BI renders them literally, and a test rejects them.

## 1. Layout grid (every page)

Units are pixels on the 1280 × 720 canvas; 16 px margins, 8 px gutters.

| Band | y | Height | Content |
|---|---|---|---|
| Header | 4 | 48 | Page title: a one-value card bound to the page's title measure (x 16, w 876, 16 pt bold); `[Data As Of Label]` card at x 900, y 8, w 364, h 40, right-aligned. Both: category label off, no padding, no text wrap, so one full line shows without clipping |
| Slicers | 56 | 48 | Synced slicer panel (below) |
| Content | 112 | 568 | KPI cards y 112–200, first row of visuals y 208–520, second row y 528–680. At most 8 data visuals (header, slicers, footer and text boxes don't count) |
| Footer | 684 | 32 | One-value card bound to `[Footer Attribution]`, directly under the content (no gap) ("Source: Dubai Land Department, CC BY 4.0 · Area locations © OpenStreetMap contributors (ODbL)"), 9 pt, `#52514e` |

**Synced slicer panel** (View → Sync slicers: sync and show on all six pages), dropdown style, single row:

| Slicer | Field | x | w | Default |
|---|---|---|---|---|
| Year | `'Date'[Year]` | 16 | 150 | **2025**, single select (the latest complete year; 2026 is partial). Save the report with it set |
| Zone / area | `'Area'[Zone]` → `'Area'[Area]` (hierarchy) | 174 | 260 | all |
| Property type | `'Property Type'[Property Type]` | 442 | 260 | all |
| Bedrooms | `'Bedrooms'[Bedrooms]` | 710 | 160 | all |
| Ready / off-plan | `'Ready Off-Plan'[Ready / Off-Plan]` | 878 | 180 | all |

Remaining width (x 1066–1264) is free for a page-specific control.

**Time-series rule.** Trend visuals show history, so for each one: Format → Edit interactions → the **Year** slicer = *None*, and a visual-level filter `'Date'[Year]` ≥ 2010 (or the start given below). Cards keep the Year filter.

**Built as PBIR.** The pages are written as PBIR JSON under `DubaiProperty.Report/definition/pages/` (Phase 5): the header title, data-as-of and footer are one-value Card visuals bound to the text measures; slicers are dropdowns in sync groups (`Year`, `Area`, `PropertyType`, `Bedrooms`, `ReadyOffPlan`); "Year slicer = None" is stored as a page `visualInteractions` entry. `tests/test_powerbi_model.py` validates every file against the official schemas, every field against the model and every formatting property against Microsoft's theme schema. Edit visuals in Desktop afterwards as usual.

**Every visual**: title on (left, 12 pt), the insight title where given, **alt text** as given (Format → General → Alt text), no borders or shadows (the theme does this), and **subtitle off** unless one is specified (newer charts add an automatic subtitle). New-card formatting is set on the card's default series (`$id = default`; in PBIR a `selector: {id: default}`), or Desktop ignores it; per-callout settings (display units) select the measure. Top-N bar charts use small category padding (inner padding 20%, 9 pt labels) so every bar fits without a scrollbar. Line charts use 2 px lines; one y-axis per chart, never a secondary axis.

---

## Page 1. Executive Overview (Q1)

Title: `[Title Executive]` (e.g. "Dubai recorded 211,007 market sales worth AED 668.3bn in 2025").

| # | Visual | Position (x, y, w, h) | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 5 callouts | 16, 112, 1036, 88 | `[Market Sales Value]` (display units Billions, 1 dp), `[Market Sales]`, `[Median Price per Sq M]`, `[Index YoY]`, `[Off-Plan Share (Value)]` | Labels: "Sales value", "Market sales", "Median AED / sq m", "Prices YoY (like for like)", "Off-plan share of value" |
| 1b | Card (new), 1 callout | 1060, 112, 204, 88 | `[Purchase Mortgage Share]` labelled **"Mortgage share (ready)"** | Subtitle **"at least – matched loans only"**: a lower bound (2025: 28% matched, up to 48% counting every ready-unit mortgage; findings §5). Own card so the caveat sits with the number |
| 2 | Line chart | 16, 208, 820, 312 | X `'Date'[Month Start]` (continuous), Y `[Market Sales Value]` (Billions) | Not filtered by Year (intentional), subtitle **"All years; not filtered by Year"**. X-axis constant lines (dashed, labels = name, above the line): 2008-09 "Global crisis", 2014-06 "2014 peak", 2020-04 "COVID" (label left), 2021-06 "2021+ boom" (label **right**, so it doesn't collide with COVID). Title: "Market sales value by month, AED" |
| 3 | Bar chart (horizontal) | 844, 208, 420, 312 | Y `'Area'[Area]`, X `[Market Sales Value]` (labels in Billions, 1 dp) | Filter: Top N 10 by `[Market Sales Value]`, sorted descending, all 10 bars visible (no scrollbar). Title: "Top 10 areas by sales value" |
| 4–6 | Three text boxes | 16 / 432 / 848, 528, 410, 152 | Insights from `reports/findings.md` (static text, bold headline + one sentence) | (4) "Off-plan is most sales but not most value: 63% of 2025 market sales but 44% of their value (69% / 50% in 2026 to date); buyers pay developers in instalments." (5) "2026 has slowed, led by ready homes: Jan–Aug −19% on 2025 (ready −37%, off-plan −7%); registration-lag checks show it is not late data." (6) "The 2009 'spike' was paperwork: 93.5% of 2009 off-plan registrations were applied for in earlier years (Law No. 13 of 2008)." |

Alt text: (1) "Six headline numbers for the selected year: sales value, number of market sales, median price per square metre, like-for-like price change, share of ready purchases with a matched mortgage, off-plan share of value." (2) "Line chart of monthly market sales value since 2004, with the 2008, 2014, 2020 and 2021 cycle points marked." (3) "Bar chart of the ten areas with the highest sales value in the selected period."

## Page 2. Financing & Market Mix (Q2)

Title: `[Title Financing]`. Trend visuals: not filtered by Year, from 2010 (subtitle says so).

| # | Visual | Position | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 4 callouts | 16, 112, 1036, 88 | `[Ready Market Sales]`, `[Purchase Mortgages]`, `[New Mortgages per 100 Sales]` (1 dp), `[Off-Plan Share (Count)]` | |
| 1b | Card (new), 1 callout | 1060, 112, 204, 88 | `[Purchase Mortgage Share]` "Mortgage share (ready)" | Subtitle "at least – matched loans only" (same card as page 1) |
| 2 | Stacked column | 16, 208, 620, 236 | X `'Date'[Month Start]`, Y `[Purchase Mortgages]` ("Matched purchase mortgage", blue) + `[Ready Sales Not Bank-Financed]` ("Not bank-financed at registration", grey; not "cash") | Year ≥ 2010. Title: "Ready sales: bank-financed at registration vs not" |
| 3 | Line chart | 644, 208, 620, 114 | X `'Date'[Month Start]`, Y `[Purchase Mortgage Share]` | **Top panel**, same x-range and width as #4. Title: "Mortgage share of ready sales (at least: matched loans only)" |
| 4 | Line chart | 644, 330, 620, 114 | X `'Date'[Month Start]`, Y `[Reference Rate]` (grey) | **Bottom panel**, aligned with #3 (no dual axis). Title: `[Reference Rate Label]` ("Fed Funds rate (EIBOR proxy …)" until EIBOR is loaded) |
| 5 | Line chart | 16, 452, 404, 228 | X `'Date'[Year]` (categorical), Y `[New Mortgages per 100 Sales]` | Subtitle "Incl. refinancing; secondary indicator. Not filtered by Year" |
| 6 | 100% stacked column | 428, 452, 404, 228 | X `'Date'[Year]`, Y `[Market Sales]`, legend `'Ready Off-Plan'[Ready / Off-Plan]` | Data labels on. Title: "Off-plan vs ready share of sales" |
| 7 | Bar chart | 840, 452, 424, 228 | Y `'Area'[Area]`, X `[Off-Plan Share (Count)]` | Top N 10 **by `[Market Sales]`** (the busiest areas; ranking by the share itself would be topped by one-sale areas), sorted by share. Title: "Off-plan share, 10 busiest areas" |

Alt text: (2) "Monthly ready sales split into those matched to a same-day purchase mortgage and those not bank-financed at registration." (3–4) "Two aligned line charts: the matched purchase-mortgage share of ready sales above, the reference interest rate below." (5) "New mortgages per 100 market sales by year." (6) "Share of market sales that were off-plan or ready, by year." (7) "Off-plan share of sales in the ten areas with the most market sales."

## Page 3. Prices & Index (Q3, Q6)

Title: `[Title Prices]`. Page control at x 1066 (not synced): `'Price Index'[Segment]`, dropdown, single select, default "Dubai (all residential)".

| # | Visual | Position | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 4 callouts | 16, 112, 1036, 88 | `[Index Value (Latest Complete)]` (1 dp), `[Index YoY]`, `[Drawdown from Peak]`, `[Area-Weighted Price per Sq M (Homes)]` | Follow the Year slicer (latest complete month in the selection) |
| 1b | Card (new), 1 callout | 1060, 112, 204, 88 | `[Max Drawdown]` "Deepest fall since 2011" | Not filtered by Year (subtitle "All years") |
| 2 | Line chart | 16, 208, 620, 220 | X `'Date'[Month Start]`, Y `[Index Value]` (blue), `[DLD Index Value]` (grey, dashed) | Year ≥ 2011, not filtered by Year. Title: "Like-for-like prices vs DLD's index (Jan 2019 = 100); ours leads by ~6 months" |
| 3 | Line chart | 644, 208, 620, 220 | X `'Date'[Month Start]`, Y `[Index Value (Apartments)]` (blue), `[Raw Median Rebased (Apartments)]` (orange) | Year ≥ 2015, not filtered by Year. Title: "Raw medians misread growth both ways: 2023 apartments +1% raw vs +17% like for like" |
| 4 | Bar chart | 16, 436, 400, 244 | Y `'Area'[Area]`, X `[Median Price per Sq M]` | Top N 10 by the same measure, sorted descending (under-min-n areas are blank and drop out). Title: "Highest median AED per sq m, top 10 areas" |
| 5 | Matrix | 424, 436, 440, 244 | Rows `'Area'[Zone]`, columns `'Bedrooms'[Bedrooms]`, values `[Median Price per Sq M]` | Visual filter Usage Group = Residential. Background colour scale `#fcfcfb` → `#9ec5f4` (light enough for black text). Blank = under min-n |
| 6 | Area chart | 872, 436, 392, 244 | X `'Date'[Month Start]`, Y `[Index Drawdown]` (orange) | Year ≥ 2011, not filtered by Year. Title: "Fall from the previous peak (2014→2020: −24% Dubai-wide)" |

Alt text: (2) "Line chart comparing this project's like-for-like price index with DLD's official index since 2011, both rebased to January 2019." (3) "Apartment price index against the raw median price per square metre, both rebased to January 2019: the gap is the mix shift." (4) "Bar chart of the ten areas with the highest median price per square metre." (5) "Table of median price per square metre by zone and bedrooms; blank cells have fewer than 20 sales." (6) "Drawdown of the selected price index from its running peak since 2011."

## Page 4. Rental Yields (Q4)

Title: `[Title Yields]`. Yields use the **last four complete quarters** and ignore the Year slicer.

| # | Visual | Position | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 3 callouts | 16, 112, 1248, 88 | `[Gross Yield (Latest 4 Quarters)]`, `[New Market Rents]`, `[Area-Weighted New Rent per Sq M (Homes)]` | Subtitle: "Gross: before service charges, vacancy and fees. Yields use the last four complete quarters" |
| 2 | Clustered bar | 16, 208, 500, 472 | Y `'Area'[Zone]`, X `[Gross Yield (Latest 4 Quarters)]`, legend `'Property Type'[Property Type]` | Visual filter Property Type ∈ {Residential · Apartment, Residential · Villa / Townhouse}; sorted descending; data labels 1 dp. Title: "Gross yield by zone, last four quarters" |
| 3 | Bar chart | 524, 208, 360, 236 | Y `'Area'[Area]`, X `[Gross Yield by Area (Latest 4 Quarters)]` | Top N 10 by the same measure, sorted descending. Title: "Highest area yields (20+ rents and sales per cell)" |
| 4 | Scatter | 892, 208, 372, 236 | Values `'Area'[Zone]`, X `[Index Growth 3Y (Zone)]`, Y `[Gross Yield (Latest 4 Quarters)]`, size `[Market Sales]` | Visual filter Property Type = Residential · Apartment; category labels on. **Manual step:** Analytics pane → X median line and Y median line (the quadrants; their PBIR binding can't be validated offline, so they aren't generated). Title: "Income vs growth (apartments): top right has both" |
| 5 | Line chart | 524, 452, 360, 228 | X `'Date'[Quarter Start]`, Y `[Gross Yield by Quarter]`, legend `'Property Type'[Property Type]` | Same type filter as #2; Year ≥ 2012, not filtered by Year. Title: "Yields fell to a 2021 low and partly recovered" |
| 6 | Column chart | 892, 452, 372, 228 | X `'Bedrooms'[Bedrooms]`, Y `[New Rent per Sq M]` | Visual filter Property Type = Residential · Apartment; data labels on. Title: "New-contract rent per sq m by bedrooms (apartments)" |

Alt text: (2) "Gross rental yield by zone for apartments and villas over the last four complete quarters." (3) "Bar chart of the ten areas with the highest gross yield, where both rents and sales reach 20 per cell." (4) "Scatter of zones: three-year price growth against gross yield for apartments, bubble size is sales." (5) "Quarterly gross yield for apartments and villas." (6) "Annual rent per square metre of new contracts by number of bedrooms, apartments."

## Page 5. Valuation Model (AVM) (Q5)

Title: `[Title Valuation]`. Page filter: `'AVM Score'[Model Set]` = Test (2025+, out of time). Page control at x 1066 (not synced): `'AVM Performance'[Breakdown]`, single select, default "Property Type" (also Reg Type, Price Band, Area, Month).

| # | Visual | Position | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 6 callouts | 16, 112, 1248, 88 | `[AVM Test MdAPE]` (2 dp), `[AVM Test Hit Rate 10%]`, `[AVM Test Hit Rate 20%]`, `[AVM Test MdAPE (Baseline)]` (2 dp), `[AVM Test Hit Rate 10% (Baseline)]`, `[AVM MdAPE Gain vs Baseline]` (2 dp) | Subtitle: "Out-of-time test set, 2025 to the snapshot (model card); not filtered by slicers" |
| 2 | Clustered bar | 16, 208, 400, 236 | Y `'AVM Performance'[Segment]`, X `[AVM Segment MdAPE]`, legend `'AVM Performance'[Model Name]` | Visual filters: Split = Test; Model ∈ {lightgbm, comps}. Title: "Median error by segment: AVM vs comparable sales" |
| 3 | Bar chart | 424, 208, 400, 236 | Y `'Feature Importance'[Feature]`, X `[Mean Abs SHAP]` | Filter Rank ≤ 10, sorted descending. Title: "What drives the valuation (mean \|SHAP\|, log points)" |
| 4 | Line chart | 832, 208, 432, 236 | X `'Date'[Month Start]`, Y `[Median Sale Price (AVM Sample)]` (blue), `[Median AVM Value]` (orange, dashed) | Not filtered by Year. Title: "Out of sample: median price vs median AVM value" |
| 5 | Table | 16, 452, 1000, 228 | `'Area'[Area]`, `'Project'[Project]`, `[Valued Sales]`, `[Median Gap %]`, `[Flagged for Review]`, `[Flagged Share]` | Top N 10 projects by `[Flagged for Review]`, sorted descending. Title: "Where sales sit furthest from the AVM (10 projects with most flags)" |
| 6 | Text box | 1024, 452, 240, 228 | | "Review flags are not accusations": flags mark sales more than 25% from their AVM value, statistical anomalies for a collateral review, not evidence of mispricing |

Alt text: (2) "Median absolute percentage error by segment for the AVM and the comparable-sales baseline on the 2025–26 test set." (3) "Top ten features by mean absolute SHAP value." (4) "Median sale price and median AVM value of out-of-sample sales by month." (5) "Table of areas and projects with the most sales flagged for review, with their median gap to the AVM."

## Page 6. Risk & Stress Test (Q6, Q7, Q9)

Title: `[Title Stress]`. **Every stress visual carries "Illustrative, not a regulatory stress test"** (subtitle).

Page controls (not synced), dropdowns, single select:

| Control | Field | Position | Default |
|---|---|---|---|
| Stress segment | `'Stress Grid'[Segment]` (visual filter Segment Level ∈ Dubai / Type / Zone; area names repeat) | 16, 112, 300, 48 | Dubai (all residential) |
| Price shock % | `'Price Shock %'[Price Shock %]` | 324, 112, 140, 48 | −20 |
| Loan-to-value | `'LTV %'[LTV Label]` | 472, 112, 300, 48 | 80% (85% = "UAE national first home cap (worst case)") |
| Replay depth | `'Replay Depth'[Replay Depth]` | 780, 112, 240, 48 | Dubai-wide (lower range) |
| Rate scenario | `'Forecast Scenario'[Scenario]` | 1028, 112, 236, 48 | Rates flat |
| Outlook segment | `'Forecast'[Segment]` | 1066, 56, 198, 48 | Dubai (all residential) |

Page filter `'Forecast'[Target]` = Price index. The synced Ready / off-plan slicer picks Ready or Off-Plan (Ready when none); off-plan is never pooled with ready.

| # | Visual | Position | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 6 callouts | 16, 168, 1248, 80 | `[Negative Equity Share]`, `[Negative Equity AED]` (Billions, 2 dp), `[Stress Purchases]`, `[Negative Equity Share (CBUAE Cap)]`, `[Negative Equity Share (Registered Loans)]`, `[Replay Negative Equity Share]` | Subtitle: "Illustrative, not a regulatory stress test. Loans held at origination; ready and off-plan never pooled" |
| 2 | Matrix (heatmap) | 16, 256, 400, 208 | Rows `'Price Shock %'[Price Shock %]`, columns `'LTV %'[LTV Label]`, values `[Negative Equity Share]` | Interactions: the Shock and LTV slicers don't filter it (it shows the whole grid). Colour scale `#fcfcfb` → `#9ec5f4`. Title: "Negative equity: shock × LTV (recent buyers)" |
| 3 | Bar chart | 424, 256, 400, 208 | Y `'Area'[Area]`, X `[Negative Equity Share by Area]` | Top N 10 by the same measure, sorted descending; property type from the synced slicer (apartments when none). Title: "Most exposed areas at the selected shock and LTV" |
| 4 | Bar chart | 832, 256, 432, 208 | Y `'Stress Replay'[Segment]`, X `[Replay Drawdown]` | Filter Used In Replay = true; the 10 deepest falls (sorted ascending). Subtitle: "Zone series are noisier and overstate it" |
| 5 | Bar chart | 16, 472, 400, 208 | Y `'Project'[Master Project]`, X `[Master Project Share (Off-Plan)]` | Top N 10 by `[Off-Plan Market Sales (Lines)]`, Master Project ≠ Unknown. Title: `[Title Concentration]`; subtitle "Proxy: developer names need the DLD projects file (Q9 deferred)" |
| 6 | Line chart (fan) | 424, 472, 840, 208 | X `'Forecast'[Month]`, Y `[Forecast Actual]` (blue), `[Forecast Central]` (orange), `[Forecast Lower 80]` and `[Forecast Upper 80]` (grey, dashed) | Month ≥ 2021-01. The 80% interval is drawn as two dashed lines, not error bars: their PBIR binding can't be validated offline (switch in Analytics → Error bars if wanted). Title: `[Title Outlook]` |

Alt text: (2) "Heatmap of the share of recent buyers in negative equity for price falls of 0 to 50% and loan-to-values of 50 to 85%." (3) "Bar chart of the ten areas with the highest negative-equity share at the selected price shock and loan-to-value." (4) "Bar chart of the ten index series with the deepest fall in the 2014 to 2020 downturn." (5) "Top ten master projects' shares of off-plan sales in the selected year, a proxy for developer concentration." (6) "Price index history since 2021 and the 12-month forecast with its 80% interval for the selected rate scenario."

---

## Checks before publishing

1. **Cards**: tick every row of `reports/kpi_reconciliation.md` §7 (regenerate with `make kpi` after any rebuild). Defaults: Year 2025, shock −20, LTV 80, Ready, Rates flat, AVM page on Test. A last-digit difference is rounding; anything more is a bug to report.
2. **Performance Analyzer** (Optimize → Performance analyzer → Refresh visuals): every visual under 1 s. The likely slow ones are the DAX medians over Transactions (page 1 card, page 3 area bar / matrix, page 5 medians); if one is over, record it and ask for a pre-aggregated rpt view rather than tuning DAX.
3. **Model size**: DAX Studio → Advanced → View Metrics (VertiPaq Analyzer); record the total and the top three tables in docs/06 §1 (estimate ≈ 45–65 MB).
4. **Accessibility**: alt text on every visual; tab order top-left to bottom-right (View → Selection → Tab order); identity never by colour alone (legends or labels).
5. **Attribution**: the footer on every page shows DLD CC BY 4.0 and OpenStreetMap ODbL.
6. Save (PBIP), then publish to My workspace → File → Embed report → Publish to web; record the URL and date in docs/08. Commit the PBIP from the Mac.
