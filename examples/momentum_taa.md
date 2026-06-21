# Momentum Tactical Asset Allocation (TAA) — `momentum_taa.py`

## Overview

This example implements a **Top-N Momentum Tactical Asset Allocation** strategy using the QSTrader backtesting framework. The strategy rotates among the 11 SPDR US Sector ETFs (e.g. `XLB`, `XLC`, `XLE`, …) by selecting the **top 3 sectors** with the highest 6-month (126 business-day) holding-period return momentum. Portfolios are rebalanced at the **end of each month**, and performance is compared against a **buy-and-hold SPY** benchmark.

---

## Strategy Logic

1. **Universe** — All SPDR US sector ETFs (`XLB`, `XLC`, `XLE`, `XLF`, `XLI`, `XLK`, `XLP`, `XLU`, `XLV`, `XLY`). Because `XLC` was not listed until June 2018, a `DynamicUniverse` is used so it is only eligible from that date onwards.
2. **Signal** — 126-business-day (≈ 6-month) holding-period return momentum, calculated via `MomentumSignal`.
3. **Alpha Model (`TopNMomentumAlphaModel`)** — At each rebalance event, ranks every eligible asset by its momentum score and assigns an **equal weight of 1/N** to the top-N assets (N = 3 by default). All other assets receive a weight of 0.
4. **Rebalance** — `end_of_month` (the last trading day of every calendar month).
5. **Burn-in** — The first year of data (1999-01-01) is used purely for signal warm-up; performance statistics begin after that date.
6. **Benchmark** — A static 100 % allocation to SPY using `FixedSignalsAlphaModel` with a `buy_and_hold` rebalance schedule.

---

## Parameters

| Parameter        | Value                           | Description                                                      |
|------------------|---------------------------------|------------------------------------------------------------------|
| `start_dt`       | 1998-12-22 14:30 UTC            | First date data is loaded (needed for the burn-in period).       |
| `burn_in_dt`     | 1999-12-22 14:30 UTC            | Date from which performance statistics are recorded.             |
| `end_dt`         | 2020-12-31 23:59 UTC            | Last date of the backtest.                                       |
| `mom_lookback`   | `126`                           | Rolling lookback window in business days (≈ 6 months).           |
| `mom_top_n`      | `3`                             | Number of top-momentum sectors held at any one time.             |
| `cash_buffer_percentage` | `0.01`                | 1 % cash buffer retained to cover transaction costs/slippage.   |

---

## Key Components

### `TopNMomentumAlphaModel`

A custom `AlphaModel` subclass that drives the rotation logic.

| Method | Description |
|--------|-------------|
| `__init__(signals, mom_lookback, mom_top_n, universe, data_handler)` | Stores references to the signals collection, lookback, top-N count, universe, and data handler. |
| `_highest_momentum_asset(dt)` | Iterates over all assets, computes their momentum score for `mom_lookback` days, and returns the top-N assets sorted by descending momentum. |
| `_generate_signals(dt, weights)` | Calls `_highest_momentum_asset` and assigns equal weight `1/mom_top_n` to each selected asset. |
| `__call__(dt)` | Entry point called at each rebalance. Returns zero weights until the signal has warmed up (`signals.warmup >= mom_lookback`), then delegates to `_generate_signals`. |

### Signal: `MomentumSignal`

Computes the holding-period return for each asset over a configurable lookback window. Registered in a `SignalsCollection` under the key `'momentum'`.

### Universe: `DynamicUniverse`

Allows assets to be added to the tradeable universe on specific dates. Used here so that `XLC` only becomes eligible after its listing date (2018-06-18).

### Data: `CSVDailyBarDataSource` + `BacktestDataHandler`

Daily OHLCV bar data is loaded from CSV files. The directory defaults to `DATA_DIR` (from `qstrader.constants`) but can be overridden with the environment variable `QSTRADER_CSV_DATA_DIR`.

---

## Data Requirements

Place the following CSV files in the data directory (default: `data/`):

**Strategy assets:** `XLB.csv`, `XLC.csv`, `XLE.csv`, `XLF.csv`, `XLI.csv`, `XLK.csv`, `XLP.csv`, `XLU.csv`, `XLV.csv`, `XLY.csv`

**Benchmark asset:** `SPY.csv`

Each CSV must contain daily OHLCV data compatible with `CSVDailyBarDataSource`.

---

## How to Run

```bash
# From the repository root
python examples/momentum_taa.py
```

To use a custom data directory:

```bash
QSTRADER_CSV_DATA_DIR=/path/to/your/csv/data python examples/momentum_taa.py
```

After the backtest completes a tearsheet is displayed comparing the strategy equity curve against the SPY benchmark, titled **"US Sector Momentum - Top 3 Sectors"**.

---

## Output

The script produces a **TearsheetStatistics** plot that includes:

- Cumulative equity curves (strategy vs. benchmark)
- Drawdown profile
- Key performance metrics (CAGR, Sharpe ratio, max drawdown, etc.)

---

## Backtest Architecture

```
CSV Files
    └─► CSVDailyBarDataSource
            └─► BacktestDataHandler
                    ├─► MomentumSignal  ──►  SignalsCollection
                    ├─► DynamicUniverse
                    └─► TopNMomentumAlphaModel
                                └─► BacktestTradingSession (end_of_month rebalance)
                                            └─► TearsheetStatistics
```

---

## Notes

- The strategy is **long-only** (`long_only=True`); it never shorts any sector.
- The equal-weighting of the top-N sectors (1/3 each) means there is no position sizing optimisation — this is intentional for simplicity.
- Momentum is purely based on past price returns; no volatility scaling or risk parity is applied.
- The burn-in year (1999) ensures that a full 126-day momentum window is available before any capital is deployed.

