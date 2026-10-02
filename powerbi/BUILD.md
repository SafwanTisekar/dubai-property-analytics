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

## 1. Layout grid and rules (every page)

Exact positions, fields, filters, titles and alt text of every visual are in **`powerbi/VISUALS.md`**, generated from the PBIR files (`make pbi-inventory`; a test fails if it is stale). This section holds the rules; the page sections below hold the intent and the decisions.

| Band | y | Height | Content |
|---|---|---|---|
| Header | 4 | 44 | Page title: one-value card bound to the page's title measure (x 16, w 876, 14 pt bold); `[Data As Of Label]` card at x 900, y 8, w 364, h 36, right-aligned. Category label off, padding 0, no wrap: one full line, no clipping |
| Slicers | 52 | 58 | Synced dropdowns: Year (x 16, w 150; default **2025**, single select), Zone / area (174, 260), Property type (442, 260), Bedrooms (710, 160), Ready / off-plan (878, 180); header 9 pt. A page-specific control may use x 1066–1264 |
| KPI cards | 116 | 100 (pages 1–3) / 84 (4–5) | New Card visuals, label + value; pages 1–3 also have a single title + subtitle card (100 px). Page 6: control row at y 116, cards at y 180 (80 px) |
| Content | 224 (pages 4–5: 208; page 6: 268) | to 680 | Usually three columns, x 16 / 428 / 840 (w 404 / 404 / 424); page 3 uses 380 / 380 / 472 so the matrix fits |
| Footer | 684 | 32 | One-value card bound to `[Footer Attribution]` (DLD CC BY 4.0 · OpenStreetMap ODbL), 9 pt, directly under the content |

**Size with Power BI's real rendered sizes, not the PBIR nominal ones.** A file that passes every nominal check can still clip on screen (gate 3: grouped KPI cards lost their labels and half their values; bar charts and the flags table scrolled). So every card height and every top-N row height assumes what Desktop actually draws, calibrated on the gates: text takes about **1.73 px per point** (an 18 pt value ≈ 31 px, a 9 pt label ≈ 16 px), a visual title ≈ 24 px, a subtitle ≈ 20 px (≈ 36 px of extra chrome on a chart), card padding ≈ 16 px, and Power BI enforces its own minimum bar and row heights. When a check passes but the page clips, the calibration is wrong: measure it in Desktop and raise the constant, never shrink the margin.

**Rules, checked by `tests/test_powerbi_model.py`:**
- **Minimum render size 240 × 180** for every chart, table and matrix: below it Power BI draws a placeholder icon (final gate: page 2's stacked panels).
- **Cards fit their rendered lines:** height ≥ padding 16 + value (pt × 1.73) + label (pt × 1.73 + 2) + title 24 + subtitle 20 + 8 margin. KPI rows show **label + value only**: no group title or subtitle on a multi-callout card (a heading, if needed, is a separate text element); a card's caveat goes in its label ("Mortgage share (ready, at least)"), not in a subtitle.
- **Top-N bar charts fit without scrolling:** height ≥ 72 + 24 × N px, + 36 with a subtitle (page 1: 10 bars in 312 px is the calibration point). **Tables:** ≥ 72 + 32 × (N + 1), no word wrap. N is chosen to fit and the title states it.
- **Static titles fit their width** (≤ width / 7 characters at 12 pt); measure-bound titles are kept short in the measure.
- **A subtitle only shows under a visible title**, so every card or chart with a subtitle has a title.
- At most 8 data visuals per page; alt text on every visual; no automatic subtitles.
- New-card formatting uses `$id = default` selectors (else Desktop ignores it); per-callout display units select the measure. Card labels 9 pt, values 18 pt.
- **Time series** ignore the Year slicer (page `visualInteractions` = none), start at the year given in their subtitle, and stop at the data snapshot (`'Date'[Is After Snapshot]` = false), so no empty 2027.
- Money is `"AED "#,0` with display units on the visual; thousands where needed come from a measure formatted `"AED "#,0"K"` (`[Median Price per Sq M (K)]`), never from scaling commas.

## Page 1. Executive Overview (Q1)

Title `[Title Executive]`. A 5-callout KPI card (sales value in Billions, 1 dp; market sales; median AED / sq m; prices YoY; off-plan share of value) and a separate **mortgage share card in the same style as the row, labelled "Mortgage share (ready, at least)"** (a lower bound, matched loans only: 2025 is 28% matched, up to 48% counting every ready-unit mortgage; findings §5). Monthly sales value line, **all years, not filtered by Year** (subtitle says so), with dashed cycle lines: Global crisis, 2014 peak, COVID, 2021+ boom (label right of the line so it clears COVID). Top-10 areas by sales value (bn labels). Three insight text boxes from `reports/findings.md` (off-plan count vs value, the 2026 slowdown, the 2009 backlog), 104 px tall so they end at the footer (no gap).

## Page 2. Financing & Market Mix (Q2)

Title `[Title Financing]`. KPI card (ready sales, matched mortgages, new mortgages per 100 sales, off-plan share by count) plus the same "Mortgage share (ready, at least)" card. Row 1: ready sales split into matched mortgage / not bank-financed (not "cash"); **mortgage share and the reference rate side by side** at full size over the same 2010-to-snapshot range (never a dual axis; final gate: the stacked panels were too small to render); the rate panel's title `[Reference Rate Label]` says "Fed Funds rate (EIBOR proxy)" until EIBOR is loaded. Row 2: new mortgages per 100 sales by year and off-plan vs ready 100% columns, both on a **continuous year axis with explicit ends 2010–2026** (horizontal labels, no scrollbar, no 2030; **update the end year when the snapshot moves into a new year**: `LAST_YEAR`, or Format → X-axis → Range in Desktop); off-plan share of the **6 busiest areas** (ranked by sales, not by share, which tiny areas would top).

## Page 3. Prices & Index (Q3, Q6)

Title `[Title Prices]`; page control: index segment (default Dubai). KPI card (index level, YoY, below previous peak, area-weighted AED / sq m of homes) and a separate card "Deepest fall since 2011" (same style as the row) that ignores Year. Ours vs DLD's index (DLD dashed, ends May 2024; ours leads by ~6 months); apartments raw median vs like for like (the mix shift: 2023 +1% raw vs +17%, in the alt text; the subtitle that overlapped the matrix header was removed); fall from the previous peak. **Price by area and the zone × bedrooms matrix are residential only and min-n 20** (visual filter `[Clean Sales]` ≥ 20 on top of the blank-under-min-n measure), the matrix (472 px wide, 8 pt) shows **Studio–4 BR** (5+ bedrooms are thin and mostly blank under min-n; no horizontal scroll) as **"18K"** (`[Median Price per Sq M (K)]`; "AED / sq m (K)" in the title), no totals, light-blue scale; the area bar shows the top 6 in AED thousands.

## Page 4. Rental Yields (Q4)

Title `[Title Yields]`. Yields use the last four complete quarters, ignore Year, and **leave out cells outside the 2–15% sanity band** (final gate: two Al Barsha, Al Quoz & Tecom cells at 25% and 23% had pushed that zone to 14.1% and the apartment headline from 7.1% to 7.2%; `reports/yields.md`, docs/06 Decisions). KPI card label + value only ("Gross yield, last 4 quarters (before costs)"). Zone bars (apartments and villas), the 6 highest area yields, the income-vs-growth scatter for apartments (the **8 zones with most sales**, labelled: Power BI labels all points or none, so the chart keeps the largest bubbles; add X / Y median lines in the Analytics pane by hand), yield trend from 2012, new rent per sq m by bedrooms (apartments, **Unknown dropped**, 8 pt labels).

## Page 5. Valuation Model (AVM) (Q5)

Title `[Title Valuation]`; page filter Model Set = Test; page control "Accuracy by" (Property Type / Reg Type / Price Band). KPI card (label + value, no group title) from **`AVM Performance`** (the model card's numbers: 6.83%, 65.0%, 88.2% vs 9.90%, 50.3%; rpt keeps 6 decimals so Power BI's half-up rounding shows 65.0%, not 65.1%). Accuracy by segment, AVM vs comparable sales, **on the same sales** (breakdowns "… (same sales)", the model card's head-to-head: villas 8.66% vs 8.51%; each model's own coverage would show LightGBM 8.91% on 21,810 villas against comparables on 20,527); **top 6 features by mean |SHAP| with readable names** (`'Feature Importance'[Feature Label]` from `seed_avm_feature_label`: Size (log sq m), Project price level (12m), Building price level (24m), Bedrooms, Master project, Area …); median price vs median AVM value by month; the 4 projects with the most review flags (no wrap; **project "Unknown" excluded**: it pools unrelated sales with no project recorded); a note that flags are statistical anomalies, not accusations.

## Page 6. Risk & Stress Test (Q6, Q7, Q9)

Title `[Title Stress]` ("… buyers in negative equity – Dubai (all residential)"). Controls (row at y 116): stress segment (Dubai / type / zone rows), price shock (−20), LTV (80%), replay depth, rate scenario; outlook segment at x 1066. KPI card, label + value only (first label "Negative equity (illustrative)"; titles of the heatmap and bars say "illustrative"): negative-equity share, shortfall (bn), purchases, at the CBUAE cap, registered loans, 2014–20 replay. **The CBUAE-cap and registered-loan cards are different rows that happen to coincide Dubai-wide** (20.69% vs 20.73%, both "20.7%"; apartments 21.7% vs 22.8%; §7 lists both to two decimals). **Heatmap: all 11 shock rows (0 to −50) at 424 px, LTV columns with short labels (`'LTV %'[LTV Short]`; 85%* = UAE national first-home cap, footnoted), no totals**; the shock and LTV slicers don't filter it. Most exposed areas (top 5), 2014→2020 fall of the 5 deepest series, master-project concentration (top 5, in a 208 px row; one-line title `[Title Concentration]`: "Top 5 master projects (top 10: 53%, HHI 399)", a proxy), the outlook (actual, forecast, dashed 80% band; **y-axis from 150** so the band is visible).

---

## Checks before publishing

1. **Cards**: tick every row of `reports/kpi_reconciliation.md` §7 (regenerate with `make kpi` after any rebuild). Defaults: Year 2025, shock −20, LTV 80, Ready, Rates flat, AVM page on Test. A last-digit difference is rounding; anything more is a bug to report.
2. **Performance Analyzer** (Optimize → Performance analyzer → Refresh visuals): every visual under 1 s. The likely slow ones are the DAX medians over Transactions (page 1 card, page 3 area bar / matrix, page 5 medians); if one is over, record it and ask for a pre-aggregated rpt view rather than tuning DAX.
3. **Model size**: DAX Studio → Advanced → View Metrics (VertiPaq Analyzer); record the total and the top three tables in docs/06 §1 (estimate ≈ 45–65 MB).
4. **Accessibility**: alt text on every visual; tab order top-left to bottom-right (View → Selection → Tab order); identity never by colour alone (legends or labels).
5. **Attribution**: the footer on every page shows DLD CC BY 4.0 and OpenStreetMap ODbL.
6. Save (PBIP), then publish to My workspace → File → Embed report → Publish to web; record the URL and date in docs/08. Commit the PBIP from the Mac.
