# Building the report in Power BI Desktop

A step-by-step guide to the six pages of docs/06 §4 on the semantic model in `DubaiProperty.SemanticModel` (Phase 5). Every field below exists in the model; every number a card shows is listed, with its filters, in **`reports/kpi_reconciliation.md` §7** (the card checklist). Measures are in the `_Measures` table, in display folders by page topic (docs/06 §3); `powerbi/measures.dax` is a readable copy.

## 0. Setup (once)

1. **No maps in v1** (decision, 2026-10-02): the Azure Maps visual needs a tenant admin to enable it, so every geographic view is a **bar chart by zone or area, top N, sorted by the same measure**. `'Area'[Latitude]` / `[Longitude]` stay in the model (OpenStreetMap centroids) for a map later. **Publish to web** is already on (docs/03 §9).
2. Close Desktop. On the Mac: start Parallels, then `make pbi-ready` (docs/03 §8).
3. If the model changed since the last open, delete `powerbi/DubaiProperty.SemanticModel/.pbi/cache.abf` (stale imported data; gitignored, rebuilt by the refresh).
4. Open `powerbi/DubaiProperty.pbip` → **Refresh**. Parameters (Transform data → Manage parameters): `PgServer` = `10.211.55.2:5432`, `PgDatabase` = `dubai_property`.
5. **The theme is registered in the PBIP** (`StaticResources/RegisteredResources/DubaiPropertyAnalytics.json`, referenced from `report.json`), so it applies on open: no manual import. The source is `powerbi/theme.json`; after editing it, copy it over the registered file (a test fails if they differ). The palette is the one the figures and the website use: blue = ready / apartments, orange = off-plan / villas, aqua = a third series, in that fixed order (colour follows the entity, never the rank). Text is `#0b0b0b` (19.2:1 on the background) and `#52514e` (7.7:1) for axis labels and subtitles; `#8a8984` is for gridlines only. Aqua, yellow and magenta are under 3:1 on the background, so **any visual that shows them also shows data labels or a legend**.
6. Canvas: every page is 16:9, **1280 × 720** (already set on the six empty pages).
7. **Money formats.** Every AED measure is formatted `"AED "#,0`. For bn / M, set the visual's **display units explicitly** (Billions or Millions, 1 decimal): *Auto* switches to Trillions on all-time totals (the Phase 5 gate showed "AED 3.6…T"). Never type Excel-style scaling commas (`#,0.0,,,"bn"`) into a format string: Power BI renders them literally, and a test rejects them.

## Redesign (Phase 5b, gate 1 built 2026-10-02)

Style modelled on a reference banking dashboard (style only; built-in visuals only, no paid or custom visuals, no third-party logos).

- **Frame on every page:** navy page background (`#1b2a4a`) forms the side bar and the frame; a grey rounded panel (`#e8ebf0`: `#f2f3f5` read as white next to the white cards; grey text stays AA at 4.8:1) holds the content. The panel is the **container background of a blank text box** (rounded border), drawn first: the same mechanism as every white card. A built-in shape's fill did not render at gate 1, which left navy titles on navy. Side bar: text logo "DUBAI PROPERTY / RISK", a vertical built-in **Page navigator** (active page white with navy text, others navy with white text) and a faint decorative house glyph.
- **Header bar:** bold uppercase title with a lighter second part ("EXECUTIVE OVERVIEW DASHBOARD"), "Data as of", a **Reset all filters** button and an **ⓘ** button that opens the KPI guide. Footer: DLD CC BY 4.0 · OpenStreetMap ODbL.
- **Reset all filters** opens a **per-page bookmark** (`definition/bookmarks/bm<Page>Reset.bookmark.json`, gate 2). The built-in Clear all slicers action left the single-select Year slicer on its value. Each bookmark captures **data only** (display state suppressed), **only that page's slicers**, and the page itself: slicers with a default go back to it (Year 2025; page 6 stress segment Dubai, shock −20, LTV 80%; page 5 Accuracy by = Property Type (same sales)), every other slicer is cleared. Generated from the slicers' own defaults and validated against Microsoft's bookmark schema; a test checks every Reset button points at its page's bookmark. **If Desktop rejects a hand-written bookmark**, recreate it by hand: set the defaults, View → Bookmarks → Add, untick Display, tick Data and Current page, Selected visuals = the page's slicers, then point the Reset button at it. Introduction and Key terms have no filters, so no Reset button.
- **Cards and sections:** every visual sits in a white rounded card with a soft shadow (theme defaults); bold section headings group them. **KPI tiles** are a value card over a grey strip with a split (Sales value → Ready · Off-plan; Median AED / sq m → Apartments · Villas; Prices YoY → Apartments · Villas; Mortgage share → matched loans · ready sales). Strips are text measures with descriptions.
- **Text cards** carry a bold heading inside the card and 12–14 px inner padding. PBIR has no documented bullet-list format for text boxes, so bullets are written to **fit on one line** (no wrapped line, so no hanging indent is needed); text-measure cards get heights sized for their rendered line count, with spare room.
- **Beginner pages:** "Introduction" and "Key terms & methods" open the report (plain English, short sentences). Every number that can change (data counts, snapshot date, AVM test size and error, today's index change, the −20% stress example, the 12-month outlook) is a measure (`Report\Guide` folder), not typed text; worked examples with round numbers are hypothetical and say so.
- **Page order:** Introduction, Key terms & methods, 1–6, KPI guide; the report opens on Introduction. At gate 1 pages 2–6 still have the previous layout and the KPI guide is a placeholder (gate 2).
- **Palette:** navy = ready / apartments, magenta `#d6247f` = off-plan / villas, greys for context; text navy (14.2:1) and grey `#5f6673` (5.8:1, AA). The reference's lighter pink (`#e83e8c`, 3.8:1) and the light context grey (`#a3a9b5`, 2.4:1) failed contrast and were replaced. `analysis/plotting.py` uses the same palette, so figures and the website match.

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

## Pages (Phase 5b redesign)

Every page: navy frame and side bar, grey panel `#e8ebf0`, header bar, white cards. Report pages 1–6 have the synced slicer row (y 60) and a "… at a glance" row of **KPI tiles** (value card + grey strip, y 148–248), then section headings with chart cards (two rows of 180 px, the render minimum, or one tall card). Exact positions, fields and alt text: `powerbi/VISUALS.md`. Page order: Introduction, Key terms, 1–6, KPI guide; the report opens on Introduction.

**Dynamic text wraps in a table, not a card.** A Card visual shows a measure's sentence on one line and cuts it (gate 1). Every measure sentence (the Introduction's data line, the Key terms live examples, the page 1 insights) is a one-column **table** named `*_text`: the column header is the card's bold heading, the value wraps at a fixed column width, and grid, totals and outlines are off. Sized from rendered lines (header ~28 px, 9 pt line ~18 px, 10 pt ~20 px). KPI strips stay one line: ≤ 26 characters at 7.5 pt, with units in the tile label.

| Page | Tiles (strip underneath) | Sections and charts |
|---|---|---|
| Introduction | none | What this report is · Why it matters · Where the data comes from (`[Guide Data Line]`) · Questions it answers · How to use it · What's on each page · Good to know |
| Key terms | none | Six property terms (definition + small AED example) · four models as analogies, each with a live example from the data (`[Guide … Line]`) · What this can't tell you |
| 1 Executive | Sales value (AED bn) [Ready · Off-plan] · Market sales [Ready · Off-plan, k] · Median AED / sq m [Apt · Villa] · Prices YoY [Apt · Villa] · Off-plan share (value) [by number] · Mortgage share (ready) [loans · sales] | Market cycles (monthly value, all years, cycle lines) · Where value concentrates (top 7 areas) · insights: off-plan count vs value, this year so far (both measures), 2009 backlog |
| 2 Financing | Ready sales [not bank-financed] · Mortgage share (ready) · New mortgages / 100 sales [count] · Off-plan share (count) [by value] · Reference rate [Fed Funds (EIBOR proxy)] | How ready buyers pay: financed vs not, mortgage share, rate (same time range, no dual axis) · Off-plan versus ready: per 100 sales, 100% columns 2010–2026, 4 busiest areas |
| 3 Prices | Index [latest complete month] · Prices YoY [Apt · Villa] · Below previous peak [deepest since 2011, all years] · AED / sq m (homes) [Apt · Villa] | How prices moved: ours vs DLD, raw median vs like for like · Falls: drawdown, top 4 areas (residential, min-n 20) · zone × Studio–4 BR matrix ("18K") in a 400 px column with **short zone labels** (`'Area'[Zone Short]`, `seed_zone_label`, ≤ 16 characters; no horizontal scroll). Control: index segment |
| 4 Yields | Gross yield [Apt · Villa] · New rent contracts [Apt · Villa] · New rent / sq m (homes) [Apt · Villa] | Gross yield, 10 busiest zones (tall card) · top 4 area yields · income vs growth (8 zones) · yields by quarter · rent / sq m by bedrooms |
| 5 Valuation | AVM median error [comparables] · Within ±10% [comparables] · Within ±20% [comparables] · Test sales valued [flagged share] | Accuracy: by segment on the same sales (labels outside the bar end, no overlap), median price vs AVM by month · Drivers and misses: top 4 drivers (readable names), 3 projects with most flags (Unknown excluded). Control: accuracy by (same-sales breakdowns) |
| 6 Risk | In negative equity [shortfall] · At the CBUAE cap [registered loans] · 2014–20 replay, Dubai-wide [own series, upper] · Price outlook, 12 months [80% range] · Top-10 master projects [HHI, proxy] | Shock × LTV heatmap (11 rows, short LTV labels, no totals) · most exposed areas · 2014–20 fall by series · top 4 master projects · price index outlook (y from 150). Controls in the slicer row: stress segment, shock %, LTV |
| KPI guide | none | Page filter (dropdown, **nothing selected**: all 27 KPIs show) and a wrapped table: #, page, KPI, meaning, how it is calculated, source table, caveats; selecting pages filters it. Sorted by "#" (report order), because KPI names repeat across pages. **Generated** from the `_Measures` descriptions of every KPI tile measure (`'KPI Guide'` calculated table, `make pbi-measures`; tests fail if a tile measure lacks a meaning, calculation or source, or the table is stale) |

**Slicer settings (tested):** Year, page 6 stress segment / shock % / LTV, page 3 index segment and page 5 accuracy-by are **single select with Require single selection** (and no select-all box); zone / area, property type, bedrooms, ready / off-plan and the KPI guide's page filter are multi-select. The **Year** slicer shows `'Date'[Year Label]` ("2026 (to 25 Sep)" marks the partial snapshot year) with a visual-level filter `'Date'[Is Data Year]` = true, so 2027 (in the calendar for the forecast) is not offered; both columns come from the snapshot date in `rpt.dim_date`, nothing is typed. If Desktop still lets you pick two years, check Format → Slicer settings → Selection on that slicer and tell me what it shows.

**Page 6 controls simplified (redesign):** the replay-depth, rate-scenario and outlook-segment slicers are gone; the measures default to Dubai-wide, Rates flat and Dubai, and the alternatives are in the strips (own-series replay, 80% range). The stress segment, shock % and LTV controls share the slicer row.

---

## Checks before publishing

1. **Cards**: tick every row of `reports/kpi_reconciliation.md` §7 (regenerate with `make kpi` after any rebuild). Defaults: Year 2025, shock −20, LTV 80, Ready, Rates flat, AVM page on Test. A last-digit difference is rounding; anything more is a bug to report.
2. **Performance Analyzer** (Optimize → Performance analyzer → Refresh visuals): every visual under 1 s. The likely slow ones are the DAX medians over Transactions (page 1 card, page 3 area bar / matrix, page 5 medians); if one is over, record it and ask for a pre-aggregated rpt view rather than tuning DAX.
3. **Model size**: DAX Studio → Advanced → View Metrics (VertiPaq Analyzer); record the total and the top three tables in docs/06 §1 (estimate ≈ 45–65 MB).
4. **Accessibility**: alt text on every visual; tab order top-left to bottom-right (View → Selection → Tab order); identity never by colour alone (legends or labels).
5. **Attribution**: the footer on every page shows DLD CC BY 4.0 and OpenStreetMap ODbL.
6. Save (PBIP), then publish to My workspace → File → Embed report → Publish to web; record the URL and date in docs/08. Commit the PBIP from the Mac.
