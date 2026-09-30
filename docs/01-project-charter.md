# 01 – Project Charter

## 1. Problem statement

Dubai's property market has been through several full cycles in two decades: the 2008–2010 crash, the 2014–2019 correction, the 2020 COVID low, and the record-breaking 2021–2025 boom driven by off-plan sales. For a **UAE bank's mortgage and real-estate risk team**, the questions are financial:

> *Where is value really being created, how much of the market is funded by debt versus cash, what are properties actually worth, and how exposed would lenders and investors be if prices corrected?*

This project acts as that team. It builds a governed data platform over the full Dubai Land Department (DLD) register, measures prices, yields and financing, builds an **automated valuation model (AVM)** and a **price index**, runs **collateral stress tests**, and delivers an executive Power BI dashboard on a public website.

## 2. Stakeholders (personas)

| Persona | Needs | Served by |
|---|---|---|
| Head of Mortgage Risk (bank) | Collateral values, LTV under stress, off-plan exposure, concentration | Valuation and Stress Test pages |
| CFO / Treasury | Market cycle, rate sensitivity (EIBOR), volume and value trends | Executive Overview, Rates |
| Real-estate investment committee (fund / family office) | Rental yield, capital growth, volatility by area | Yields and Price Index pages |
| Credit / collateral valuation team | Fair value of a specific unit vs its transaction price | AVM page |

## 3. Business questions

| # | Question | Technique | Output |
|---|---|---|---|
| Q1 | How have transaction volume and value moved through each market cycle since 2004? | SQL aggregation, cycle annotation | Executive Overview |
| Q2 | How much of the market is financed: mortgage vs cash, and off-plan vs ready? Has that shifted with EIBOR? | Transaction-group analysis, rates join | Financing page |
| Q3 | What is the price per sq m by area, property type and bedrooms, and how fast is it growing? | SQL + hedonic price index | Price Index page |
| Q4 | Where are gross rental yields highest and lowest, and are they compressing? | Sales × Ejari rent join | Yields page |
| Q5 | What is a property's fair value? Which transactions look over- or under-priced? | **AVM** (LightGBM), SHAP | Valuation page |
| Q6 | How volatile is each area, and what were its historical peak-to-trough drawdowns? | Index volatility, drawdown analysis | Risk page |
| Q7 | If prices fall 10/20/30%, what share of recent buyers at typical LTVs would be in negative equity, and where? | Scenario stress test | Stress Test page (what-if sliders) |
| Q8 | Where are prices heading over the next 12 months under different rate paths? | Time-series forecast with rate drivers | Outlook section |
| Q9 | How concentrated is off-plan supply by developer and area? | Concentration (HHI), pipeline from Projects | Risk page |

## 4. KPIs (canonical definitions)

| KPI | Definition |
|---|---|
| Market sales (count / AED) | Rows where `is_market_sale = 1` (sales procedures only; excludes gifts, inheritance, mortgages) |
| Median price per sq m | Median of `price_per_sqm` over clean market sales |
| Price index | Hedonic time-dummy index, base = 100 at Jan 2019 (see docs/05) |
| YoY price growth | Index this month ÷ index 12 months earlier − 1 |
| Mortgage share | Mortgage registrations ÷ (mortgage registrations + market sales), by month |
| Off-plan share | Off-plan market sales ÷ market sales (count and value) |
| Gross rental yield | Median annual rent ÷ median sale price, for the same area × property sub-type × bedrooms × quarter |
| AVM accuracy | Median absolute % error (MdAPE); hit rate within ±10% and ±20% |
| Max drawdown | Largest peak-to-trough fall in an area's index |
| Negative-equity share (scenario) | % of recent purchases where loan (price × LTV) > shocked value |
| Developer concentration | Herfindahl–Hirschman Index (HHI) of off-plan sales value by developer |

## 5. Scope

**In scope:** DLD transactions (full history), Ejari rent contracts, DLD reference tables (projects, buildings, units, lookups), EIBOR / Fed Funds / Brent, the AVM, the hedonic price index, yield analytics, stress testing, a forecast, and the Power BI report and website.

**Out of scope:** individual owner or party-level data (none is published, and none will be sought), scraping listing portals (terms of use), and anything presented as investment or lending advice. The stress test is **illustrative**, using stated assumptions.

## 6. Success criteria

| Area | Criterion |
|---|---|
| Engineering | Full pipeline reproducible from a clean clone via `make pipeline`; incremental monthly top-up works; under 20 min on a laptop |
| Data quality | 100% of dbt tests pass; raw → gold reconciliation of counts and AED totals; every exclusion rule logged with row counts |
| Data science | AVM beats the comparable-median baseline on the out-of-time test (MdAPE and ±10% hit rate); hedonic index correlates strongly with DLD's official index |
| BI | Every KPI reconciles to SQL; each page answers its questions at a glance; loads in under 5 s |
| Portfolio | Live website with the embedded report, case study, methodology and public GitHub repo |

## 7. Why this matters for UAE employers

This is the work UAE banks, developers, funds and regulators actually do: collateral valuation (AVMs), mortgage LTV monitoring, off-plan concentration risk, rental-yield analysis and rate sensitivity under the AED–USD peg. Say so explicitly on the website.

## 8. Decisions log

| Date | Decision | Reason |
|---|---|---|
| 2026-09-29 | Domain: Dubai property market with a mortgage/investment-risk lens, using DLD open data | Dubai-specific, large, public, financial; aligns with the UAE job market |
| 2026-09-29 | PostgreSQL 18 (local, Homebrew) + dbt, Power BI Service, GitHub Pages | Free, industry-standard RDBMS, no usage limits; replaces the earlier DuckDB choice |
| 2026-09-30 | dbt-core 1.12 + dbt-postgres 1.11; `dbt_expectations` from the `metaplane` fork | 1.10 is deprecated; calogica's `dbt_expectations` is archived and metaplane maintains it with the same macro names |
| 2026-09-30 | Database created with `C` collation (UTF-8 encoding) | Byte-order sorting is fast and identical on macOS and the Linux CI container, so tests don't depend on OS locale |
| 2026-09-30 | Trained model binaries go to gitignored `artifacts/models/`, not under `src/` | Keeps large binaries out of git without an ignore pattern that could hit the `dubai_property.models` package |
