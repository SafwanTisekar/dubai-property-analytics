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

- **Method:** time-dummy hedonic regression. `log(ppsqm) ~ property characteristics + area fixed effects + month dummies`. Month coefficients give the index (Jan 2019 = 100). Fit separately for Dubai overall, apartments vs villas, and the top zones (min-n rule; fall back to quarterly if sparse). **As built (Phase 4a):** rolling-window time dummy (36-month windows stepped 12 months, chained on the overlapping periods), from Jan 2011, villas on bedroom-known sales only; the pooled fit is the robustness check. Results: `reports/price_index.md`; table `ml.fct_price_index`, view `rpt.price_index`.
- **Why hedonic:** raw median prices are biased by mix shifts. In a boom, more cheap off-plan studios sell, which drags medians down even when like-for-like prices rise. Show that effect explicitly on the website: it's a strong insight.
- **Validation:** correlate the index with DLD's official Residential Price Index (target: correlation ≥ 0.9 on growth rates) and discuss the differences. **As built:** YoY of our index averaged over the trailing 12 months vs DLD's YoY: 0.93 Dubai, 0.92 apartments, 0.91 villas (2012-12 to 2024-05; DLD's file ends in May 2024). Month for month 0.68–0.72, with ours leading DLD by ~6 months (§8).
- **Derived risk metrics:** YoY growth, 12-month rolling volatility, drawdown from the running peak, and peak-to-trough episodes (2008–2011, 2014–2019, 2020).

## 3. Rental yield analytics: core

- Join **new** Ejari contracts and clean market sales on area × sub-type × bedrooms × quarter (plus project where n is sufficient).
- `gross_yield = median annual rent / median sale price`. Require n ≥ 20 on both sides, otherwise roll up to the zone level. Report the sample sizes.
- Outputs: yield by area (map), yield vs 3-year price growth scatter (the "income vs growth" quadrant), yield compression over time, and apartments vs villas.
- Caveat: gross yield excludes service charges, vacancy and fees. Say so.
- **As built (Phase 4a):** sale side = clean **ready** sales; rent side = `is_market_rent` (new, single-line contracts: C11 option 1). Area cells and zone cells (medians recomputed from rows) with n ≥ 20 on both sides; 2–15% sanity band flagged, not dropped. Results: `reports/yields.md`; table `ml.agg_yield_quarter`, view `rpt.yield_quarter`. Project-level cells are not built (area cells already need 20 ready sales of one bedroom count per quarter, which only the busiest areas reach).

## 4. Collateral stress test: core (illustrative)

**Question:** if prices fall X%, what share of recent buyers would be in negative equity at typical loan-to-value (LTV) ratios, and in which areas?

- **Population:** clean market sales in the last 24–36 months (the recent-vintage buyers).
- **Assumed loan** = price × LTV, with an LTV scenario grid (50%, 60%, 70%, 80%). Default the caps to CBUAE mortgage rules (seed `seed_ltv_rules`: verified against the CBUAE rulebook 2026-09-30 and dated with `effective_from` / `effective_to`, so a purchase uses the caps in force on its date). Off-plan uses a lower LTV assumption.
- **Current value** = purchase price × (index today / index at purchase) for the property's segment (mark-to-market via the hedonic index).
- **Shock grid:** −0% to −50% in 5% steps. Also run **historical replay scenarios**: apply each area's actual 2008–2011 and 2014–2019 drawdowns.
- **Note for 4c (owner, 2026-10-01): the 2008–11 replay is dropped.** The hedonic index starts in January 2011 (§8), so no 2008–11 drawdown can be measured. 4c uses **the shock grid plus one historical replay: the 2014→2020 episode**, peak to trough (Dubai **−24%**: June 2014 → September 2020; apartments −25%, villas −30%), applied per segment from `ml.fct_price_index`: the zone × type series where one is published, else the type series. A 2008-style crash remains covered by the grid's −40% / −50% steps, labelled as hypothetical.
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
- **A 2008–10 index from on-time registrations only** (logged 2026-10-01): restrict 2008–10 to sales registered in the year they were applied for (`transaction_id` year = registration year), which drops the Law 13/2008 backlog (F1.3), then chain it to the published 2011+ index. If it validates (no 2009 "rise"; a peak-to-trough in line with published accounts of the crash), it would restore the 2008–11 replay for the stress test. Risks: on-time registrations in 2008 are a small, selective sample (mostly ready units in older areas), and the year-boundary effect (deals applied in December, registered in January) needs a month-level rule rather than a calendar-year one.

## 7. Deliverables

- `reports/avm_model_card.md`: purpose, data, split, features, metrics by segment, SHAP, limitations
- `reports/price_index.md`: method, validation vs the DLD index, mix-shift illustration
- `reports/stress_test.md`: assumptions, LTV sources, results, caveats
- `reports/figures/*.png`
- PostgreSQL `ml.*` tables listed in docs/04 §3

## 8. Decisions log

| Date | Decision | Reason |
|---|---|---|
| 2026-10-01 | **Hedonic index published as a rolling-window time dummy (RTD)**: 36-month windows stepped 12 months, chained by the mean log gap over the 24 shared periods; every segment, monthly or quarterly. The pooled 2011–2026 fit is kept as the robustness check | Owner decision after the check came out material: the apartment off-plan premium moved from +6% (2011–13 window) to +38% (2023–25), and the pooled index differs from RTD by up to 10–11% in level (Dubai, apartments; 15% villas) and 11–21 pp in YoY. RTD also validates better against DLD (aligned YoY r 0.93 / 0.92 / 0.91 vs 0.92 / 0.90 / 0.86 for the pooled fit in the 2008-start trial run) |
| 2026-10-01 | **Index starts in January 2011** (not 2008) | In 2009–10, 30–50% of clean apartment sales were registered after their application year (Law 13/2008 backlog, findings F1.3), so prices dated from the earlier boom and a 2008-start index rose through the 2009 crash. Starting in 2011 doesn't change the validation. Consequence: the 2008–11 episode and the stress test's 2008–11 historical replay (§4) are out of scope (owner decision) |
| 2026-10-01 | **Validation headline = timing-aligned**: our index averaged over the trailing 12 months vs DLD, lag 0; raw month-for-month figures and the best lead shown alongside | Owner decision. Ours leads DLD by ~6 months (best raw YoY r at a 5–6 month lead); a 12-month trailing mean of ours lines up at lag 0, which suggests DLD's monthly figure averages the last 12 months. An inference: DLD's file has no methodology |
| 2026-10-01 | **DLD file: validate on `*_monthly_index`**, not `*_price_index` | `*_index` is a ratio (Jan 2012 = 1.000); `*_price_index` is an AED level of a typical unit whose ratio to the index drifts by ~8%, so it isn't a rescaled index. The file's 2026-09-01 stamp is a load time: its data ends in May 2024 |
| 2026-10-01 | **Villas: bedroom-known sales only**, bedroom dummies as the main size control, ln(area) secondary | Bedroom-less villa areas are plot-sized (findings F3.1) and their share fell over time, which alone would move a per-sq-m index. With ln(area) as a regressor, per-sq-m and per-unit dependent variables give the same period effects. Cost: 32,357 villa sales since 2011 left out |
| 2026-10-01 | **Estimation: exact OLS via sparse normal equations** (scipy), not statsmodels | ~0.9M rows × a few hundred dummies: dense statsmodels needs GBs, while XᵀX is small. Full train ~30 s |
| 2026-10-01 | **Frequency rule:** monthly if ≥ 90% of months from the segment's first 20+ month pass min-n, else quarterly on the same basis, else not published; the base period must pass | Judging a zone from 2011 would fail zones developed later (MBR City, DIFC); a base-month miss (Emirates Hills) falls back to quarterly instead of dropping the zone |
| 2026-10-01 | **Noise gate:** a segment whose period-on-period log changes have SD > 0.10 isn't published | Set after the first full run (so it is data-informed, and logged here for that reason): every segment was ≤ 0.09 except JVC villas (quarterly, 0.16, a 69% one-quarter jump, a base quarter that put the whole series at ~200 before 2019). Every level is relative to one base period, so a noisy base distorts all of them |
| 2026-10-01 | **Episodes:** ≥ 10% from the running peak, peak until the peak is regained; no expected list imposed; dips down and back within ~2 months labelled "likely noise" | Owner instruction. Result: 2014–2020 is one episode (−24% Dubai, trough Sep 2020, recovered Nov 2022) |
| 2026-10-01 | **No confidence band published** for the index | Within-window SEs ignore chaining uncertainty and would overstate precision; `n_obs` per period is published instead |
| 2026-10-01 | **Yields: ready sales only** on the price side; rents = new single-line contracts (C11 option 1) | An off-plan price buys a unit that can't be let yet, often on a payment plan; a multi-unit contract's per-unit rent is an allocation, not a price |
| 2026-10-01 | **Stress test (4c): shock grid + 2014→2020 replay; 2008–11 replay dropped.** A 2008–10 index from on-time registrations is logged as a stretch item (§6) | Owner decision. The published index starts in 2011, so a 2008–11 drawdown can't be measured; the 2014→2020 episode (−24% Dubai) is the one historical decline in range, and the −40% / −50% grid steps cover a 2008-size shock hypothetically |
| 2026-10-01 | **Yields: zone medians recomputed from rows** (SQL grouping sets), not averaged from area medians; yields outside 2–15% kept and flagged | Medians don't average. Out-of-band cells pass min-n and are usually sub-market mismatches (8 of 5,919), not errors |
