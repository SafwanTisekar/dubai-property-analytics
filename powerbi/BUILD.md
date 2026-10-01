# Building the report in Power BI Desktop

A step-by-step guide to the six pages of docs/06 §4 on the semantic model in `DubaiProperty.SemanticModel` (Phase 5). Every field below exists in the model; every number a card shows is listed, with its filters, in **`reports/kpi_reconciliation.md` §7** (the card checklist). Measures are in the `_Measures` table, in display folders by page topic (docs/06 §3); `powerbi/measures.dax` is a readable copy.

## 0. Setup (once)

1. **Power BI Service, Admin portal → Tenant settings → Integration settings → enable "Use Azure Maps visual"** (the map visual on pages 3, 4 and 6). **Publish to web** is already on (docs/03 §9). Desktop: File → Options → Global → Security → *Use Azure Maps visual* ticked as well.
2. Close Desktop. On the Mac: start Parallels, then `make pbi-ready` (docs/03 §8).
3. If the model changed since the last open, delete `powerbi/DubaiProperty.SemanticModel/.pbi/cache.abf` (stale imported data; gitignored, rebuilt by the refresh).
4. Open `powerbi/DubaiProperty.pbip` → **Refresh**. Parameters (Transform data → Manage parameters): `PgServer` = `10.211.55.2:5432`, `PgDatabase` = `dubai_property`.
5. **View → Themes → Browse for themes → `powerbi/theme.json`.** The palette is the one the figures and the website use: blue = ready / apartments, orange = off-plan / villas, aqua = a third series, in that fixed order (colour follows the entity, never the rank). Text is `#0b0b0b` (19.2:1 on the background) and `#52514e` (7.7:1) for axis labels and subtitles; `#8a8984` is for gridlines only. Aqua, yellow and magenta are under 3:1 on the background, so **any visual that shows them also shows data labels or a legend**.
6. Canvas: every page is 16:9, **1280 × 720** (already set on the six empty pages).
7. **Money formats.** Every AED measure is formatted `"AED "#,0`. For bn / M, set the visual's **display units explicitly** (Billions or Millions, 1 decimal): *Auto* switches to Trillions on all-time totals (the Phase 5 gate showed "AED 3.6…T"). Never type Excel-style scaling commas (`#,0.0,,,"bn"`) into a format string: Power BI renders them literally, and a test rejects them.

## 1. Layout grid (every page)

Units are pixels on the 1280 × 720 canvas; 16 px margins, 8 px gutters.

| Band | y | Height | Content |
|---|---|---|---|
| Header | 8 | 40 | Page title text box (x 16, w 860; the page's insight title measure where given, else static); `[Data As Of Label]` card at x 900, w 364, right-aligned, label off |
| Slicers | 56 | 48 | Synced slicer panel (below) |
| Content | 112 | 572 | The page's visuals (≤ 8 data visuals; header, slicers and footer don't count) |
| Footer | 692 | 24 | Text box from `[Footer Attribution]` ("Source: Dubai Land Department, CC BY 4.0 · Area locations © OpenStreetMap contributors (ODbL)"), 9 pt, `#52514e` |

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

**Every visual**: title on (left, 12 pt), the insight title where given, **alt text** as given (Format → General → Alt text), no borders or shadows (the theme does this). Line charts use 2 px lines; one y-axis per chart, never a secondary axis.

---

## Page 1. Executive Overview (Q1)

Title: `[Title Executive]` (e.g. "Dubai recorded 211,007 market sales worth AED 668.3bn in 2025").

| # | Visual | Position (x, y, w, h) | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 6 callouts | 16, 112, 1248, 96 | `[Market Sales Value]` (display units Billions, 1 dp), `[Market Sales]`, `[Median Price per Sq M]`, `[Index YoY]`, `[Purchase Mortgage Share]`, `[Off-Plan Share (Value)]` | Labels: "Sales value", "Market sales", "Median AED / sq m", "Prices YoY (like for like)", "Ready purchases with a mortgage (lower bound)", "Off-plan share of value" |
| 2 | Line chart | 16, 216, 820, 300 | X `'Date'[Month Start]` (continuous), Y `[Market Sales Value]` (Billions) | Time-series rule from 2004. X-axis constant lines with labels: 2008-09 "Global crisis", 2014-06 "2014 peak", 2020-04 "COVID", 2021-06 "2021+ boom". Title: "Market sales value by month, AED" |
| 3 | Bar chart (horizontal) | 844, 216, 420, 300 | Y `'Area'[Area]`, X `[Market Sales Value]` (Billions) | Filter: Top N 10 by `[Market Sales Value]`. Title: "Top 10 areas by sales value" |
| 4–6 | Three text boxes | 16 / 432 / 848, 524, 408, 160 | Insights from `reports/findings.md` | (4) `[Title Off-Plan]` + "Off-plan is most sales but not most value: buyers of off-plan units pay developers in instalments." (5) "2026 has slowed, led by ready homes: Jan–Aug −19% on 2025 (ready −37%, off-plan −7%); registration-lag checks show it is not late data." (6) "The 2009 'spike' was paperwork: 93.5% of 2009 off-plan registrations were applied for in earlier years (Law No. 13 of 2008)." |

Alt text: (1) "Six headline numbers for the selected year: sales value, number of market sales, median price per square metre, like-for-like price change, share of ready purchases with a matched mortgage, off-plan share of value." (2) "Line chart of monthly market sales value since 2004, with the 2008, 2014, 2020 and 2021 cycle points marked." (3) "Bar chart of the ten areas with the highest sales value in the selected period."

## Page 2. Financing & Market Mix (Q2)

Title: `[Title Financing]`.

| # | Visual | Position | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 5 callouts | 16, 112, 1248, 80 | `[Ready Market Sales]`, `[Purchase Mortgages]`, `[Purchase Mortgage Share]`, `[New Mortgages per 100 Sales]`, `[Off-Plan Share (Count)]` | |
| 2 | Stacked column | 16, 200, 620, 230 | X `'Date'[Month Start]`, Y `[Purchase Mortgages]` + `[Ready Sales Not Bank-Financed]` | Time-series rule from 2010. Legend renamed "Matched purchase mortgage" / "Not bank-financed at registration" (not "cash"). Title: "Ready sales: bank-financed at registration vs not" |
| 3 | Line chart | 644, 200, 620, 150 | X `'Date'[Month Start]`, Y `[Purchase Mortgage Share]` | Time-series rule from 2010. **Top panel** of the stack: same x-range and width as #4 |
| 4 | Line chart | 644, 354, 620, 150 | X `'Date'[Month Start]`, Y `[Reference Rate]` | **Bottom panel**, aligned with #3 (no dual axis). Title: `[Reference Rate Label]` (shows "Fed Funds rate (EIBOR proxy …)" until EIBOR is loaded) |
| 5 | Line chart | 644, 512, 620, 172 | X `'Date'[Year]`, Y `[New Mortgages per 100 Sales]` | Time-series rule from 2010. Title: "New mortgages per 100 market sales (incl. refinancing; secondary indicator)" |
| 6 | 100% stacked column | 16, 438, 300, 246 | X `'Date'[Year]`, Y `[Market Sales]`, legend `'Ready Off-Plan'[Ready / Off-Plan]` | Time-series rule from 2010. Data labels on (orange slot). Title: "Off-plan vs ready share of sales" |
| 7 | Bar chart | 324, 438, 312, 246 | Y `'Area'[Area]`, X `[Off-Plan Share (Count)]` | Top N 15 by `[Market Sales]`. Title: "Off-plan share, 15 busiest areas" |

Alt text: (2) "Monthly ready sales split into those matched to a same-day purchase mortgage and those not bank-financed at registration." (3–4) "Two aligned line charts: the matched purchase-mortgage share of ready sales above, the reference interest rate below." (5) "New mortgages per 100 market sales by year." (6) "Share of market sales that were off-plan or ready, by year." (7) "Off-plan share of sales in the 15 busiest areas."

## Page 3. Prices & Index (Q3, Q6)

Title: `[Title Prices]`. Page control at x 1066: slicer `'Price Index'[Segment]`, dropdown, single select, default "Dubai (all residential)" (not synced).

| # | Visual | Position | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 5 callouts | 16, 112, 1248, 80 | `[Index Value (Latest Complete)]`, `[Index YoY]`, `[Drawdown from Peak]`, `[Max Drawdown]`, `[Area-Weighted Price per Sq M (Homes)]` | `[Max Drawdown]`: Year slicer = None (whole history) |
| 2 | Line chart | 16, 200, 620, 240 | X `'Date'[Month Start]`, Y `[Index Value]`, `[DLD Index Value]` | Time-series rule from 2011. Legend: "Hedonic index (this project)" / "DLD official index (ends May 2024)". Title: "Like-for-like prices vs DLD's index (Jan 2019 = 100); ours leads by ~6 months" |
| 3 | Line chart | 644, 200, 620, 240 | X `'Date'[Month Start]`, Y `[Index Value (Apartments)]`, `[Raw Median Rebased (Apartments)]` | Time-series rule from 2015. Title: "Raw medians misread growth both ways: 2023 apartments +1% raw vs +17% like for like" |
| 4 | Azure map (bubble) | 16, 448, 400, 236 | Latitude `'Area'[Latitude]`, Longitude `'Area'[Longitude]`, size `[Market Sales]`, bubble colour `[Median Price per Sq M]` (gradient `#cde2fb` → `#184f95`) | Tooltip: `'Area'[Area]`, `'Area'[Zone]`. Title: "Median AED per sq m by area" |
| 5 | Matrix | 424, 448, 440, 236 | Rows `'Bedrooms'[Bedrooms]`, columns `'Area'[Zone]`, values `[Median Price per Sq M]` | Visual filter `'Property Type'[Usage Group]` = Residential. Background conditional format, blue ramp. Blank = under min-n. Title: "Median AED per sq m: bedrooms × zone" |
| 6 | Area chart | 872, 448, 392, 236 | X `'Date'[Month Start]`, Y `[Index Drawdown]` | Time-series rule from 2011. Title: "Fall from the previous peak (2014→2020: −24% Dubai-wide)" |

Alt text: (2) "Line chart comparing this project's like-for-like price index with DLD's official index since 2011, both rebased to January 2019." (3) "Apartment price index against the raw median price per square metre, both rebased to January 2019: the gap is the mix shift." (4) "Map of Dubai areas: bubble size is the number of sales, colour the median price per square metre." (5) "Table of median price per square metre by bedrooms and zone; blank cells have fewer than 20 sales." (6) "Drawdown of the price index from its running peak."

## Page 4. Rental Yields (Q4)

Title: `[Title Yields]`. Yields use the **last four complete quarters** and ignore the Year slicer.

| # | Visual | Position | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 3 callouts | 16, 112, 1248, 80 | `[Gross Yield (Latest 4 Quarters)]`, `[New Market Rents]`, `[Area-Weighted New Rent per Sq M (Homes)]` | Card subtitle: "Gross: before service charges, vacancy and fees" |
| 2 | Clustered bar | 16, 200, 500, 484 | Y `'Area'[Zone]`, X `[Gross Yield (Latest 4 Quarters)]`, legend `'Property Type'[Property Type]` | Visual filter Property Type ∈ {Residential · Apartment, Residential · Villa / Townhouse}. Data labels on. Title: "Gross yield by zone, last four quarters" |
| 3 | Azure map (bubble) | 524, 200, 360, 240 | Lat / long from `'Area'`, colour `[Gross Yield by Area (Latest 4 Quarters)]`, size `[Market Sales]` | Title: "Area yields (only areas with 20+ rents and sales per cell)" |
| 4 | Scatter | 892, 200, 372, 240 | Values `'Area'[Zone]`, X `[Index Growth 3Y (Zone)]`, Y `[Gross Yield (Latest 4 Quarters)]`, size `[Market Sales]` | Visual filter Property Type = Residential · Apartment (one type). Analytics: X median line and Y median line (quadrants). Data labels (zone) on. Title: "Income vs growth: top right has both" |
| 5 | Line chart | 524, 448, 360, 236 | X `'Date'[Quarter Start]`, Y `[Gross Yield by Quarter]`, legend `'Property Type'[Property Type]` | Same type filter as #2; time-series rule from 2012. Title: "Yields fell to a 2021 low and partly recovered" |
| 6 | Column chart | 892, 448, 372, 236 | X `'Bedrooms'[Bedrooms]`, Y `[New Rent per Sq M]` | Visual filter Property Type = Residential · Apartment. Title: "New-contract rent per sq m by bedrooms (apartments)" |

Alt text: (2) "Gross rental yield by zone for apartments and villas over the last four complete quarters." (3) "Map of area-level gross yields where both rents and sales reach 20 per cell." (4) "Scatter of zones: three-year price growth against gross yield, bubble size is sales." (5) "Quarterly gross yield for apartments and villas." (6) "Annual rent per square metre of new contracts by number of bedrooms."

## Page 5. Valuation Model (AVM) (Q5)

Title: `[Title Valuation]`. Page filter: `'AVM Score'[Model Set]` = Test (2025+, out of time). Page control at x 1066: slicer `'AVM Performance'[Breakdown]`, single select, values Property Type / Reg Type / Price Band, default Property Type.

| # | Visual | Position | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 6 callouts | 16, 112, 1248, 80 | `[AVM Test MdAPE]`, `[AVM Test Hit Rate 10%]`, `[AVM Test Hit Rate 20%]`, `[AVM Test MdAPE (Baseline)]`, `[AVM Test Hit Rate 10% (Baseline)]`, `[AVM MdAPE Gain vs Baseline]` | Labels "AVM", "Comparable sales (baseline)"; these read the model card's numbers and ignore slicers |
| 2 | Clustered bar | 16, 200, 400, 260 | Y `'AVM Performance'[Segment]`, X `[AVM Segment MdAPE]`, legend `'AVM Performance'[Model Name]` | Visual filters: Split = Test; Model ∈ {lightgbm, comps}. Title: "Median error by segment: AVM vs comparable sales" |
| 3 | Bar chart | 424, 200, 400, 260 | Y `'Feature Importance'[Feature]`, X `[Mean Abs SHAP]` | Filter `'Feature Importance'[Rank]` ≤ 15; sort by value. Title: "What drives the valuation (mean \|SHAP\|, log points)" |
| 4 | Line chart | 832, 200, 432, 260 | X `'Date'[Month Start]`, Y `[Median Sale Price (AVM Sample)]`, `[Median AVM Value]` | Year slicer = None. Title: "Out of sample: median price vs median AVM value by month" |
| 5 | Table | 16, 468, 1000, 216 | `'Area'[Area]`, `'Project'[Project]`, `[Valued Sales]`, `[Median Gap %]`, `[Flagged for Review]`, `[Flagged Share]` | Top N 15 by `[Flagged for Review]`; `[Median Gap %]` diverging background (blue ↔ red, grey midpoint at 0). Title: "Where sales sit furthest from the AVM" |
| 6 | Text box | 1024, 468, 240, 216 | | "Review flags mark sales more than 25% from their AVM value: statistical anomalies for a collateral review, **not** accusations of mispricing. The register records no floor, view, condition or sale circumstances." |

Alt text: (2) "Median absolute percentage error by segment for the AVM and the comparable-sales baseline on the 2025–26 test set." (3) "Top 15 features by mean absolute SHAP value." (4) "Median sale price and median AVM value of out-of-sample sales by month." (5) "Table of areas and projects with the most sales flagged for review, with their median gap to the AVM."

## Page 6. Risk & Stress Test (Q6, Q7, Q9)

Title: `[Title Stress]`; subtitle text box under it: `[Stress Disclaimer]` ("Illustrative, not a regulatory stress test…"). **Every stress visual carries that label** (subtitle or footnote).

Page controls (not synced), in the slicer band from x 1066 and in a left rail if needed:
- `'Price Shock %'[Price Shock %]`: slider, single value, default **−20**.
- `'LTV %'[LTV Label]`: buttons, single select, default **80%** (85% = "UAE national first home cap (worst case)").
- `'Stress Grid'[Segment]`: dropdown, single select, visual filter Segment Level ∈ {Dubai, Type, Zone}, default "Dubai (all residential)".
- `'Replay Depth'[Replay Depth]`: buttons, default "Dubai-wide (lower range)".
- `'Forecast Scenario'[Scenario]` and `'Forecast'[Segment]`: dropdowns, defaults "Rates flat", "Dubai (all residential)"; also filter `'Forecast'[Target]` = Price index on the page.
- The synced Ready / off-plan slicer picks Ready or Off-Plan (Ready when none). Off-plan is never pooled with ready.

| # | Visual | Position | Fields | Settings |
|---|---|---|---|---|
| 1 | Card (new), 6 callouts | 16, 112, 1248, 80 | `[Negative Equity Share]`, `[Negative Equity AED]` (Billions), `[Stress Purchases]`, `[Negative Equity Share (CBUAE Cap)]`, `[Negative Equity Share (Registered Loans)]`, `[Replay Negative Equity Share]` | |
| 2 | Matrix (heatmap) | 16, 200, 400, 240 | Rows `'Price Shock %'[Price Shock %]`, columns `'LTV %'[LTV Label]`, values `[Negative Equity Share]` | Edit interactions: Shock and LTV slicers = None on this visual (it shows the whole grid). Background colour scale `#fcfcfb` → `#184f95`. Title: "Negative equity: shock × LTV (recent buyers, loans at origination)" |
| 3 | Azure map (bubble) | 424, 200, 400, 240 | Lat / long from `'Area'`, colour `[Negative Equity Share by Area]`, size `[Market Sales]` | Property type from the synced slicer (apartments when none). Title: "Negative equity by area at the selected shock and LTV" |
| 4 | Bar chart | 832, 200, 432, 240 | Y `'Stress Replay'[Segment]`, X `[Replay Drawdown]` | Visual filter Used In Replay = true. Title: "2014→2020 replay: the fall each index series took (zone series overstate it)" |
| 5 | Bar chart | 16, 448, 400, 236 | Y `'Project'[Master Project]`, X `[Master Project Share (Off-Plan)]` | Top N 10 by `[Off-Plan Market Sales (Lines)]`; filter Master Project ≠ Unknown. Title: `[Title Concentration]`. Footnote: "Proxy: developer names need the DLD projects file (Q9 deferred)" |
| 6 | Line chart (fan) | 424, 448, 840, 236 | X `'Forecast'[Month]`, Y `[Forecast Actual]`, `[Forecast Central]` | Visual filter Month ≥ 2021-01-01. Analytics → Error bars on `[Forecast Central]`: upper `[Forecast Upper 80]`, lower `[Forecast Lower 80]`, shaded band (a second band for 95% if legible). Title: `[Title Outlook]` |

Alt text: (2) "Heatmap of the share of recent buyers in negative equity for price falls of 0 to 50% and loan-to-values of 50 to 85%." (3) "Map of the negative-equity share by area at the selected price shock and loan-to-value." (4) "Bar chart of each index series' fall in the 2014 to 2020 downturn." (5) "Top ten master projects' shares of off-plan sales, a proxy for developer concentration." (6) "Price index history since 2021 and the 12-month forecast with its 80% interval for the selected rate scenario."

---

## Checks before publishing

1. **Cards**: tick every row of `reports/kpi_reconciliation.md` §7 (regenerate with `make kpi` after any rebuild). Defaults: Year 2025, shock −20, LTV 80, Ready, Rates flat, AVM page on Test. A last-digit difference is rounding; anything more is a bug to report.
2. **Performance Analyzer** (Optimize → Performance analyzer → Refresh visuals): every visual under 1 s. The likely slow ones are the DAX medians over Transactions (page 1 card, page 3 maps / matrix, page 5 medians); if one is over, record it and ask for a pre-aggregated rpt view rather than tuning DAX.
3. **Model size**: DAX Studio → Advanced → View Metrics (VertiPaq Analyzer); record the total and the top three tables in docs/06 §1 (estimate ≈ 45–65 MB).
4. **Accessibility**: alt text on every visual; tab order top-left to bottom-right (View → Selection → Tab order); identity never by colour alone (legends or labels).
5. **Attribution**: the footer on every page shows DLD CC BY 4.0 and OpenStreetMap ODbL.
6. Save (PBIP), then publish to My workspace → File → Embed report → Publish to web; record the URL and date in docs/08. Commit the PBIP from the Mac.
