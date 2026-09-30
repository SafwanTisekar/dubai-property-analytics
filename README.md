# Dubai Property Market & Mortgage Risk Analytics

**An end-to-end financial analytics project on the full Dubai Land Department (DLD) register: ~1.5M+ property transactions (~1 GB) and the full Ejari rent register (~4.4 GB across 11 files, likely 10M+ contract lines) since 2004, joined with UAE interest rates.**

Built with SQL (PostgreSQL + dbt), Python (Polars, LightGBM, statsmodels, SHAP) and Power BI Service, and published on a portfolio website with an embedded interactive dashboard.

---

## The business question

> *For a UAE bank's mortgage and real-estate risk team: where is value being created in Dubai property, how much of it is funded by debt, what are properties really worth, and how exposed would lenders and investors be if prices corrected?*

1. **Cycles.** How have volumes and values moved through the 2008, 2014 and 2020 cycles and the 2021+ boom?
2. **Financing.** Mortgage vs cash, off-plan vs ready. How does the mix react to EIBOR?
3. **Prices.** A hedonic price index that strips out mix shift, compared against DLD's official index.
4. **Yields.** Gross rental yield by community, from matching sales and Ejari rents.
5. **Valuation.** An automated valuation model (AVM) for residential units, as banks use for collateral.
6. **Risk.** Volatility, drawdowns, developer concentration in off-plan.
7. **Stress test.** Negative-equity exposure of recent buyers under price shocks and LTV scenarios.
8. **Outlook.** A 12-month price forecast under rate scenarios.

## Data

| Source | Content | Licence |
|---|---|---|
| Dubai Land Department Open Data / Dubai Pulse | Transactions (sales, mortgages, gifts), Ejari rents, projects, buildings, units, valuations, developers | CC BY 4.0 |
| Central Bank of the UAE | EIBOR, banking/real-estate credit statistics | Public |
| FRED | Fed Funds (AED–USD peg), Brent crude | Public |

## Architecture

```
DLD / Dubai Pulse / CBUAE / FRED CSVs ─► Python COPY loader ─► PostgreSQL: BRONZE (raw)
      ─► dbt ─► SILVER (typed, cleaned) ─► GOLD (star schema)
      ─► Python ML: AVM · hedonic index · yields · stress test · forecast ─► ML schema
      ─► dbt reporting views (rpt) ─► Power BI (PostgreSQL connector, import) ─► Power BI Service ─► Publish to web
      ─► GitHub Pages website (iframe embed)
```

## Documentation

| Doc | What it covers |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Instructions for Claude Code |
| [01 – Project charter](docs/01-project-charter.md) | Problem, personas, questions, KPIs, scope, success criteria |
| [02 – Data sources](docs/02-data-sources.md) | DLD datasets, access routes, key fields, known issues |
| [03 – Architecture](docs/03-architecture.md) | Stack, medallion layers, repo layout, setup, Power BI licensing |
| [04 – Pipeline & data quality](docs/04-pipeline-and-data-quality.md) | Ingestion, cleaning rules, star schema, tests |
| [05 – Data science](docs/05-data-science.md) | AVM, hedonic index, yields, stress test, forecast |
| [06 – Power BI](docs/06-power-bi.md) | Semantic model, DAX, report pages, publishing |
| [07 – Website](docs/07-website.md) | Site structure, embed, hosting |
| [08 – Roadmap](docs/08-roadmap.md) | Phases with ready-to-paste Claude Code prompts |

## Quick start (once built)

```bash
make setup      # uv environment
make db         # create Postgres database, roles, schemas
make download   # DLD increments, rates (bulk CSVs placed in data/raw manually)
make pipeline   # bronze → silver → gold → models → rpt views
make update     # monthly incremental refresh
make test
```

---

*Author: Safwan Tisekar. Data: Dubai Land Department (CC BY 4.0), Central Bank of the UAE, FRED. Independent portfolio project, not affiliated with DLD, and not investment or lending advice.*
