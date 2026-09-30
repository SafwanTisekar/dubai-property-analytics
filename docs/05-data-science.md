# 05 – Data Science

Five components, in priority order. Components 1–3 are core; 4–5 are core but lighter; the stretch items are optional.

## 1. Automated Valuation Model (AVM): core

**Goal:** predict the fair market price per sq m of a residential unit at a given date. Banks use AVMs for mortgage collateral checks. Output: `avm_value` and `avm_gap_pct = (price − avm_value) / avm_value` for every clean market sale.

**Population:** clean residential market sales (`is_market_sale = 1`, no quality flags, not bulk deals), apartments and villas/townhouses. Model off-plan and ready properties together with an `is_offplan` feature, then report accuracy for each.

**Target:** `log(price_per_sqm)`. Convert back with a smearing correction or median calibration.

**Features (known at transaction time only)**

| Group | Features |
|---|---|
| Location | `area_id` (categorical), zone, `master_project`, project (target-encoded **within the training window only**), nearest metro/mall/landmark (categorical + missing flag) |
| Property | sub-type, bedrooms, `log(area_sqm)`, has_parking, is_penthouse, is_offplan, property age at sale (from Projects/Buildings completion date; negative = off-plan) |
| Time | months since 2004, month of year |
| Market state (lagged) | Area median price/sq m over the previous 3 and 12 months (**computed strictly from earlier transactions**), area sales volume over the previous 3 months, EIBOR 3M at the transaction month |
| Developer | Developer (for off-plan), developer's number of past projects |

**Leakage rules:** rolling or lagged features must use only transactions **before** the row's date (window functions with `ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING` on date-ordered data, or an as-of join). Target encoding is fitted on the training period only. A pytest checks that every lag feature at date *d* uses only data dated before *d*.

**Out-of-time split**

| Set | Dates | Purpose |
|---|---|---|
| Train | 2010-01 → 2023-12 | Fit (pre-2010 is too sparse and too crisis-distorted; test including it as an ablation) |
| Validation | 2024-01 → 2024-12 | Tuning, early stopping |
| Test | 2025-01 → latest | Final reported numbers |

**Models**
1. **Baseline (comparable sales):** median price/sq m of the same area × sub-type × bedrooms over the previous 6 months.
2. **Hedonic OLS:** log-linear regression. It's interpretable and also produces the price index (§2).
3. **LightGBM:** native categoricals, early stopping, Optuna tuning (≤ 50 trials).

**Evaluation (on test, overall and by segment: ready vs off-plan, apartment vs villa, price band, top 20 areas)**
- **MdAPE** (median absolute % error), the headline AVM metric
- **Hit rate:** % of predictions within ±10% and ±20% of the actual price, the industry-standard AVM measures
- MAPE, R² on log price
- Error by month (does accuracy decay during fast-moving markets?)

**Explainability:** SHAP global importance, dependence plots (size, bedrooms, age, area), plus three worked examples for the website ("why this 2-bed in Dubai Marina was valued at AED X").

**Use of the gap:** flag transactions > 25% above or below the AVM as "potential mispricing / collateral review", aggregated by area and developer. Present these as statistical anomalies, not accusations.

## 2. Hedonic price index: core

- **Method:** time-dummy hedonic regression. `log(ppsqm) ~ property characteristics + area fixed effects + month dummies`. Month coefficients give the index (Jan 2019 = 100). Fit separately for Dubai overall, apartments vs villas, and the top zones (min-n rule; fall back to quarterly if sparse).
- **Why hedonic:** raw median prices are biased by mix shifts. In a boom, more cheap off-plan studios sell, which drags medians down even when like-for-like prices rise. Show that effect explicitly on the website: it's a strong insight.
- **Validation:** correlate the index with DLD's official Residential Price Index (target: correlation ≥ 0.9 on growth rates) and discuss the differences.
- **Derived risk metrics:** YoY growth, 12-month rolling volatility, drawdown from the running peak, and peak-to-trough episodes (2008–2011, 2014–2019, 2020).

## 3. Rental yield analytics: core

- Join **new** Ejari contracts and clean market sales on area × sub-type × bedrooms × quarter (plus project where n is sufficient).
- `gross_yield = median annual rent / median sale price`. Require n ≥ 20 on both sides, otherwise roll up to the zone level. Report the sample sizes.
- Outputs: yield by area (map), yield vs 3-year price growth scatter (the "income vs growth" quadrant), yield compression over time, and apartments vs villas.
- Caveat: gross yield excludes service charges, vacancy and fees. Say so.

## 4. Collateral stress test: core (illustrative)

**Question:** if prices fall X%, what share of recent buyers would be in negative equity at typical loan-to-value (LTV) ratios, and in which areas?

- **Population:** clean market sales in the last 24–36 months (the recent-vintage buyers).
- **Assumed loan** = price × LTV, with an LTV scenario grid (50%, 60%, 70%, 80%). Default the caps to CBUAE mortgage rules (seed `seed_ltv_rules`, **verify current rules and cite them**). Off-plan uses a lower LTV assumption.
- **Current value** = purchase price × (index today / index at purchase) for the property's segment (mark-to-market via the hedonic index).
- **Shock grid:** −0% to −50% in 5% steps. Also run **historical replay scenarios**: apply each area's actual 2008–2011 and 2014–2019 drawdowns.
- **Outputs** (`ml_stress_grid`): count and share of properties with loan > shocked value, AED of negative equity, by area / zone / off-plan flag. Power BI what-if sliders pick the shock and LTV.
- **If Phase 1 confirms that mortgage rows carry real loan amounts**, add a second view on registered mortgages (actual loan vs indexed value = estimated current LTV). Otherwise state clearly that LTVs are assumptions.
- Label everything **illustrative, not a regulatory stress test**.

## 5. Market outlook forecast: lighter

- **Target:** monthly hedonic index (Dubai overall + apartments + villas), and monthly sales volume.
- **Models:** seasonal naive baseline → SARIMAX with exogenous EIBOR 3M (lagged) → optionally LightGBM on lag features. Rolling-origin backtest over the last 24 months, reporting MAPE per horizon (1, 3, 6, 12 months).
- **Scenarios:** rates flat / +100bp / −100bp, to show rate sensitivity. Show fan charts and be honest about uncertainty.

## 6. Stretch

- **Off-plan concentration risk:** HHI of off-plan sales by developer and area; the pipeline of units due for handover by year (Projects table) vs historical absorption.
- **Area segmentation:** k-means on (yield, 3y growth, volatility, liquidity) → investment "personas" per area.
- **Rent vs buy calculator** on the website (static JS using exported area medians).

## 7. Deliverables

- `reports/avm_model_card.md`: purpose, data, split, features, metrics by segment, SHAP, limitations
- `reports/price_index.md`: method, validation vs the DLD index, mix-shift illustration
- `reports/stress_test.md`: assumptions, LTV sources, results, caveats
- `reports/figures/*.png`
- PostgreSQL `ml.*` tables listed in docs/04 §3

## 8. Decisions log

| Date | Decision | Reason |
|---|---|---|
| | | |
