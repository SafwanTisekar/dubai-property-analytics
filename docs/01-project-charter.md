# 01. Project charter

What the project is for, the questions it answers, how its KPIs are defined and the rules every part of the pipeline follows.

## 1. Problem

Dubai's property market has been through several full cycles in twenty years: the 2008–10 crash, the 2014–19 correction, the 2020 COVID low and the 2021–25 boom led by off-plan sales. The project takes the view of a **UAE bank's mortgage and real-estate risk team**:

> *Where is value being created, how much of the market is funded by debt, what are properties worth, and how exposed would lenders and investors be if prices corrected?*

It builds a tested data platform over the full Dubai Land Department (DLD) register, measures prices, yields and financing, fits an **automated valuation model (AVM)** and a **hedonic price index**, runs an illustrative **collateral stress test**, and publishes the results as a Power BI report embedded in a website.

## 2. Stakeholders

| Persona | Needs | Served by |
|---|---|---|
| Head of Mortgage Risk (bank) | Collateral values, LTV under stress, off-plan exposure, concentration | Valuation and Risk pages |
| CFO / Treasury | Market cycle, rate sensitivity, volume and value trends | Executive Overview, Financing |
| Investment committee (fund / family office) | Rental yield, capital growth, volatility by area | Prices and Yields pages |
| Collateral valuation team | Fair value of a unit vs its transaction price | Valuation page |

## 3. Business questions

| # | Question | Technique | Output |
|---|---|---|---|
| Q1 | How have transaction volume and value moved through each cycle since 2004? | SQL aggregation, cycle annotation | Executive Overview |
| Q2 | How much of the market is bank-financed, and how does off-plan compare with ready? Has the mix moved with rates? | Purchase-mortgage matching, rates join | Financing page |
| Q3 | What is the price per sq m by area, type and bedrooms, and how fast is it growing? | SQL + hedonic price index | Prices page |
| Q4 | Where are gross rental yields highest and lowest, and are they compressing? | Sales × Ejari rents | Yields page |
| Q5 | What is a property's fair value? Which sales look over- or under-priced? | AVM (LightGBM), SHAP | Valuation page |
| Q6 | How volatile is each area, and what were its peak-to-trough drawdowns? | Index volatility, drawdowns | Prices and Risk pages |
| Q7 | If prices fall 10/20/30%, what share of recent buyers would be in negative equity, and where? | Scenario stress test | Risk page (what-if slicers) |
| Q8 | Where are prices heading over the next 12 months under different rate paths? | SARIMAX with a rate driver | Risk page (outlook) |
| Q9 | How concentrated is off-plan supply by developer and area? | HHI | Risk page (master-project proxy until developer data is loaded) |

## 4. KPIs (canonical definitions)

| KPI | Definition |
|---|---|
| Market sales (count / AED) | Rows where `is_market_sale = 1` (arm's-length sales procedures; excludes gifts, grants, lease-to-own and mortgages). AED counted once per deal |
| Median price per sq m | Median of `price_per_sqm` over clean market sales |
| Price index | Hedonic rolling-window time-dummy index, Jan 2019 = 100 (docs/05 §2) |
| YoY price growth | Index this month ÷ index 12 months earlier − 1 |
| Purchase-mortgage share of ready sales | Ready market sales matched to a same-day purchase mortgage of the same unit (`has_purchase_mortgage`: Mortgage Registration ↔ Sell, Delayed Mortgage ↔ Delayed Sell, unit key unique on both sides, `int_purchase_mortgage_pairs`) ÷ ready market sales, by year. A **lower bound**; the upper bound is all Mortgage Registration / Delayed Mortgage lines ÷ ready sales (includes refinancing). Unmatched sales are "not bank-financed at registration", not "cash" (off-plan buyers mostly pay developers in instalments). Portfolio mortgages are reported separately (deals and AED, once per deal) |
| New mortgages per 100 market sales (secondary) | Individual new mortgages (`is_new_mortgage`: Mortgage Registration, Delayed Mortgage, Mortgage Pre-Registration; includes refinancing) × 100 ÷ market sales |
| Off-plan share | Off-plan market sales ÷ market sales (count and value) |
| Gross rental yield | Median annual rent ÷ median sale price, same area × property type × bedrooms × quarter |
| AVM accuracy | Median absolute % error (MdAPE); hit rate within ±10% and ±20% |
| Max drawdown | Largest peak-to-trough fall in an index series |
| Negative-equity share (scenario) | % of recent purchases where loan (price × LTV) > shocked value |
| Developer concentration | Herfindahl–Hirschman Index (HHI) of off-plan sales value |

## 5. Scope

**In scope:** DLD transactions (full history), Ejari rent contracts, the DLD Residential Sale Index (benchmark), Fed Funds / Brent / EIBOR, the AVM, the hedonic index, yields, the stress test, a forecast, the Power BI report and the website.

**Out of scope:** owner- or party-level data (none is published and none is sought), scraping listing portals, and anything presented as investment or lending advice. The stress test is **illustrative** and states its assumptions.

## 6. Success criteria

| Area | Criterion |
|---|---|
| Engineering | Full pipeline reproducible from a clean clone via `make pipeline`, under 20 min on a laptop |
| Data quality | 100% of dbt tests pass; raw → gold reconciliation of counts and AED totals; every exclusion logged with row counts |
| Data science | AVM beats the comparable-sales baseline out of time (MdAPE and ±10% hit rate); hedonic index tracks DLD's official index |
| BI | Every card reconciles to SQL; each page answers its questions at a glance |
| Portfolio | Live website with the embedded report and a public repository |

## 7. Project rules

Code comments cite this section as "docs/01 §7".

**Domain**
- Only arm's-length market sales feed prices, indices, yields and the AVM. Gifts, inheritance, grants and mortgage rows are excluded via `seed_procedure_map` (`is_market_sale`); mortgages are analysed separately.
- Off-plan vs ready (`reg_type`) is a first-class dimension everywhere.
- Areas are in **sq m** and money in **AED**. A sq ft view, if ever shown, converts explicitly (1 sq m = 10.7639 sq ft).
- Multi-unit rent contracts repeat the amount on every line: rule C11 (docs/04 §2) applies before any rent is summed.
- Market rent means **new contracts**; renewals lag the market.
- **Min-n:** no median, yield or index point is published for a segment with fewer than 20 observations; roll up to the zone instead.
- Arabic (`_ar`) columns are dropped in silver. No party- or owner-level data is ever sought.

**Data science**
- **No look-ahead:** every lag or rolling feature at date *d* uses only data dated before *d*; a pytest enforces it.
- **Out-of-time splits only** (train ≤ 2023, validation 2024, test 2025+), never random.
- AVM metrics are MdAPE and ±10% / ±20% hit rates, always shown against the comparable-sales baseline.
- An AVM MdAPE below ~3% or a ±10% hit rate above ~90% is treated as leakage until proven otherwise (`config.LEAKAGE_*` alarms).
- The stress test uses assumed LTVs with the CBUAE source cited in `seed_ltv_rules`, and is labelled illustrative.

**Engineering**
- ELT: Python only loads raw CSVs into `bronze` (all `text`, no transformation) with `COPY`. All typing, cleaning and modelling of data happens in dbt.
- No full tables in pandas: aggregate in SQL, read model-sized frames with connectorx, write back with `COPY`.
- Rent detail never goes to Power BI; it gets rent aggregates only.
- Every step that filters rows logs row counts in and out with the reason. Quality issues become flags; rows are never silently deleted.
- Thresholds live in `config.py` or dbt vars. Credentials come only from `.env`.
- Gold AED is `numeric(18,2)`; rates are decimals (0.0525, not 5.25).
- Power BI connects as the read-only `pbi_reader` role and reads only `rpt.*` views; import mode, no Python/R visuals, all measures in the model.
- Attribution "Dubai Land Department, CC BY 4.0" appears in the report footer and on the website.

## 8. Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-09-29 | Domain: Dubai property market with a mortgage/investment-risk lens, using DLD open data | Dubai-specific, large, public, financial; aligns with the UAE job market |
| 2026-09-29 | PostgreSQL 18 (local, Homebrew) + dbt, Power BI Service, GitHub Pages | Free, industry-standard RDBMS, no usage limits; replaces the earlier DuckDB choice |
| 2026-09-30 | dbt-core 1.12 + dbt-postgres 1.11; `dbt_expectations` from the `metaplane` fork | 1.10 is deprecated; calogica's `dbt_expectations` is archived and metaplane maintains it with the same macro names |
| 2026-09-30 | Database created with `C` collation (UTF-8 encoding) | Byte-order sorting is fast and identical on macOS and the Linux CI container, so tests don't depend on OS locale |
| 2026-09-30 | Mortgage share counts individual new mortgages only; portfolio mortgages reported separately (docs/04 Decisions) | A portfolio loan covers several units, which would distort a per-purchase ratio |
| 2026-09-30 | Trained model binaries go to gitignored `artifacts/models/`, not under `src/` | Keeps large binaries out of git without an ignore pattern that could hit the `dubai_property.models` package |
| 2026-09-30 | Phase 3 answers Q1–Q3 with a Q4 preview; **Q9 deferred** | Developer concentration needs developer names from the DLD projects file, which is not loaded (docs/08 Phase 0) |
| 2026-09-30 | **Trend and rate analysis starts in 2010**; 2004–08 volumes are shown but labelled as ready-only | Off-plan sales of 2004–08 were registered in 2009–10 (reports/findings.md F1.3–F1.4), so earlier volumes and mortgage shares aren't comparable |
| 2026-09-30 | **Mix shift measured by a fixed-basket like-for-like change** (zone × bedrooms cells with n ≥ 20 in both years, base-year sales weights) | Simple and explainable; it shows why Phase 4 needs a hedonic index without pre-empting it |
| 2026-09-30 | **Yield preview grain = zone × class × bedrooms, last 12 months, ready sales only**, min-n on both sides, cells outside 2–15% left out | Rent comes from ready units, so off-plan prices would understate yields; bedroom matching avoids comparing 1-bed rents with 3-bed prices. The proper grain (area × sub-type × quarter) is Phase 4 |
| 2026-09-30 | **Fed Funds is the rate proxy** until EIBOR is loaded; rate links are reported as associations | The AED is pegged to the USD; CBUAE has no stable EIBOR download (docs/04 Decisions) |
| 2026-09-30 | **Mortgage share replaced by the purchase-mortgage share of ready sales**; new mortgages per 100 market sales kept as a secondary indicator | The old ratio, new mortgages ÷ (new mortgages + market sales), double-counted: a mortgaged purchase registers both a sale and a mortgage, and new mortgages include refinancing. Matching the two legs of one purchase gives a numerator that is a subset of its denominator (docs/04 Decisions) |
