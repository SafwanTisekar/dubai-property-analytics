"""Phase 3 exploratory analysis (docs/08): SQL over gold / rpt, returning small DataFrames.

Every function aggregates in Postgres and returns at most a few thousand rows, so the
notebooks never pull ``fct_transaction`` or ``fct_rent_contract`` lines into pandas
(docs/01 §7). The notebooks in ``notebooks/`` only call these functions and plot.

Modules:
    common: snapshot date, SQL runner, min-n masking, partial-year helper.
    market_cycles: Q1, sales volume and value through the cycles, the 2009 spike.
    financing: Q2, mortgage share vs Fed Funds, off-plan share, observed LTVs, portfolios.
    prices_rents: Q3 / Q4 preview, AED per sq m, rents, top areas, mix shift, yields.
    plotting: one chart style for every figure in reports/figures/.
"""
