# 06 – Power BI Report

## 1. Data connection

- **Source: PostgreSQL** `dubai_property` on the Mac, via Get Data → **PostgreSQL database**, **Import mode** (required for Publish to web). Connection details over the Parallels network are in docs/03 §8.
- Log in as the read-only role **`pbi_reader`**, and select only **`rpt.*` views** (e.g. `rpt.transactions`, `rpt.rent_contracts`, `rpt.dim_area`, `rpt.price_index`, `rpt.stress_grid`). All business logic lives in dbt; Power Query only confirms data types.
- Server and database are **Power BI parameters** (`PgServer`, `PgDatabase`), so switching between the Parallels IP and localhost is one change.
- Save as a **Power BI Project (.pbip)** for git, and attach a `.pbix` to GitHub Releases.
- Refresh happens in Desktop (the Mac must be on, with Postgres running), then republish. No gateway is needed because the public report is republished from Desktop rather than refreshed in the Service.
- Model budget: transactions (~1.6M rows) + **rent aggregates only** (`rpt.rent_month`, a few hundred thousand rows; the 10M+ contract lines stay in Postgres) + small aggregates and ML tables. Target a .pbix under 300 MB: round AED to whole numbers in the `rpt` views, keep high-cardinality text (building names) only in dimension views, and exclude `_ar` columns.

## 2. Semantic model

- Star schema as in docs/04 §3; single-direction one-to-many relationships.
- `dim_date` (day grain) marked as the date table; facts join on date.
- `dim_area` and `dim_property_type` are shared by the sales, rent and aggregate facts, so one slicer filters everything.
- Display folders: **Market, Financing, Prices, Yields, Valuation, Risk, Rates**.
- What-if parameters: `Price Shock %` (0 to −50, step 5) and `LTV %` (50–85, step 5).
- Format: AED with `"AED "#,0,,"M"` / `"AED "#,0.0,,,"bn"`; percentages to one decimal place.

## 3. Core DAX measures

```dax
// ---------- Market ----------
Market Sales = CALCULATE ( COUNTROWS ( fct_transaction ), fct_transaction[is_market_sale] = 1, fct_transaction[has_quality_flag] = 0 )

Market Sales Value = CALCULATE ( SUM ( fct_transaction[price_aed] ), fct_transaction[is_market_sale] = 1, fct_transaction[has_quality_flag] = 0 )

Sales Value YoY % =
VAR _cy = [Market Sales Value]
VAR _py = CALCULATE ( [Market Sales Value], SAMEPERIODLASTYEAR ( dim_date[date] ) )
RETURN DIVIDE ( _cy - _py, _py )

Median Price per Sqm =
CALCULATE ( MEDIAN ( fct_transaction[price_per_sqm] ), fct_transaction[is_market_sale] = 1, fct_transaction[has_quality_flag] = 0 )

// ---------- Financing ----------
Mortgage Registrations = CALCULATE ( COUNTROWS ( fct_transaction ), fct_transaction[procedure_category] = "mortgage" )

Mortgage Share = DIVIDE ( [Mortgage Registrations], [Mortgage Registrations] + [Market Sales] )

Off-plan Share (Value) =
DIVIDE ( CALCULATE ( [Market Sales Value], fct_transaction[is_offplan] = 1 ), [Market Sales Value] )

Avg EIBOR 3M = AVERAGE ( fct_rates_monthly[eibor_3m] )

// ---------- Prices / index ----------
Price Index = AVERAGE ( fct_price_index[index_value] )     // filter segment via slicer

Index YoY % = AVERAGE ( fct_price_index[yoy] )

Drawdown from Peak = MIN ( fct_price_index[drawdown_from_peak] )

// ---------- Yields ----------
// Rents come pre-aggregated (agg_rent_month); weighted average of medians is an approximation, so show exact medians from agg_yield_quarter where precision matters
New Rent Contracts = CALCULATE ( SUM ( agg_rent_month[contracts] ), agg_rent_month[is_new] = 1 )

Avg Annual Rent per Sqm (New) =
CALCULATE (
    DIVIDE ( SUMX ( agg_rent_month, agg_rent_month[median_rent_per_sqm] * agg_rent_month[contracts] ), SUM ( agg_rent_month[contracts] ) ),
    agg_rent_month[is_new] = 1
)

Gross Yield = AVERAGE ( agg_yield_quarter[gross_yield] )    // pre-computed with min-n rule

// ---------- Valuation (AVM) ----------
AVM MdAPE = MEDIAN ( fct_transaction[avm_abs_pct_error] )

AVM Hit Rate ±10% =
DIVIDE (
    CALCULATE ( COUNTROWS ( fct_transaction ), fct_transaction[avm_abs_pct_error] <= 0.10, fct_transaction[model_set] = "test" ),
    CALCULATE ( COUNTROWS ( fct_transaction ), fct_transaction[model_set] = "test" )
)

Flagged for Review = CALCULATE ( COUNTROWS ( fct_transaction ), ABS ( fct_transaction[avm_gap_pct] ) > 0.25 )

// ---------- Stress test ----------
Selected Shock = SELECTEDVALUE ( 'Price Shock %'[Price Shock % Value], -0.20 )
Selected LTV   = SELECTEDVALUE ( 'LTV %'[LTV % Value], 0.80 )

Negative Equity Share =
CALCULATE (
    DIVIDE ( SUM ( ml_stress_grid[negative_equity_count] ), SUM ( ml_stress_grid[purchases] ) ),
    ml_stress_grid[shock_pct] = [Selected Shock],
    ml_stress_grid[ltv_pct] = [Selected LTV]
)

Negative Equity AED =
CALCULATE (
    SUM ( ml_stress_grid[negative_equity_aed] ),
    ml_stress_grid[shock_pct] = [Selected Shock],
    ml_stress_grid[ltv_pct] = [Selected LTV]
)
```

The shock and LTV values are stored as integers (e.g. −20, 80) in both the parameter tables and `ml_stress_grid`, to avoid floating-point equality issues. Adjust the measures accordingly. `tests/test_kpi_reconciliation.py` reproduces every KPI in docs/01 §4 in SQL, and the Power BI cards must match before publishing.

## 4. Report pages

16:9 canvas, a consistent header (title, "Source: Dubai Land Department (CC BY 4.0)", data-as-of date), a synced slicer panel (Year, Zone/Area, Property sub-type, Bedrooms, Off-plan/Ready) and one theme.

| # | Page | Answers | Visuals |
|---|---|---|---|
| 1 | **Executive Overview** | Q1 | KPI cards (Sales Value, Sales Count, Median AED/sq m, Index YoY, Mortgage Share, Off-plan Share) · sales value by month with **cycle annotations** (2008, 2014, 2020, 2021+) · top 10 areas by value · 3 insight text boxes |
| 2 | **Financing & Market Mix** | Q2 | Mortgage vs cash stacked area by month · mortgage share vs EIBOR 3M (dual axis) · off-plan vs ready share over time · off-plan share by area bar |
| 3 | **Prices & Index** | Q3, Q6 | Hedonic index lines (Dubai / apartments / villas / zones) vs DLD official index · **raw median vs hedonic** (mix-shift story) · AED/sq m by area map · bedrooms × zone matrix · drawdown chart |
| 4 | **Rental Yields** | Q4 | Yield by area map · yield vs 3-year growth scatter (bubble = sales volume; quadrant lines) · yield trend by zone · rent per sq m by bedrooms |
| 5 | **Valuation Model (AVM)** | Q5 | AVM KPI cards (MdAPE, ±10%/±20% hit rates vs baseline) · accuracy by segment bar · top feature importance · actual vs predicted by month · table of the largest AVM gaps by area/project |
| 6 | **Risk & Stress Test** | Q6, Q7, Q9 | **Price Shock** and **LTV** sliders → Negative Equity Share and AED cards · negative-equity share by area map/bar · historical drawdown replay · developer concentration (HHI, top developers' off-plan share) · 12-month outlook fan chart |

**Maps:** test the map visual in Publish to web early. Filled/shape maps need an area boundary TopoJSON (check Dubai Municipality or Dubai Pulse open data for community boundaries); otherwise use a bubble map on area centroids from `seed_area`. **No Python/R visuals**; SHAP images go on the website.

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
