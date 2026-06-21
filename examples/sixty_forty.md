# 60/40 US Equities/Bonds Portfolio — `sixty_forty.py`

## Overview

This example implements a classic **60/40 Multi-Asset Portfolio** using the QSTrader backtesting framework. The portfolio allocates **60% to US Equities** (via the `SPY` ETF) and **40% to US Aggregate Bonds** (via the `AGG` ETF). The portfolio is rebalanced back to target weights at the **end of each calendar month**. Strategy performance is evaluated against a **100% buy-and-hold SPY** benchmark over the period from September 2003 through December 2019.

---

## Strategy Logic

1. **Universe** — `StaticUniverse` consisting of two equity asset identifiers: `EQ:SPY` (S&P 500 ETF) and `EQ:AGG` (iShares Core U.S. Aggregate Bond ETF).
2. **Alpha Model (`FixedSignalsAlphaModel`)** — Returns static target portfolio weights at every rebalancing date:
   - `EQ:SPY`: **0.60** (60%)
   - `EQ:AGG`: **0.40** (40%)
3. **Rebalance Schedule** — `end_of_month` (triggers rebalancing on the final business day of each calendar month to restore target target weights).
4. **Execution Constraints** — `long_only=True` with a `cash_buffer_percentage=0.01` (1% cash buffer reserved for market orders and uninvested residuals).
5. **Benchmark** — A `StaticUniverse` containing `EQ:SPY` with 100% allocation (`FixedSignalsAlphaModel({'EQ:SPY': 1.0})`) on a `buy_and_hold` rebalance schedule (rebalanced once at inception).

---

## Parameters

| Parameter | Value | Description |
|---|---|---|
| `start_dt` | `2003-09-30 14:30:00 UTC` | Start date of the backtest simulation. |
| `end_dt` | `2019-12-31 23:59:00 UTC` | End date of the backtest simulation. |
| `strategy_symbols` | `['SPY', 'AGG']` | Ticker symbols representing the 60/40 strategy assets. |
| `rebalance` (Strategy) | `'end_of_month'` | Rebalances strategy weights on the last business day of every month. |
| `rebalance` (Benchmark) | `'buy_and_hold'` | Rebalances benchmark weights once at backtest inception. |
| `long_only` | `True` | Restricts portfolio holdings to long positions only. |
| `cash_buffer_percentage` | `0.01` | Retains 1% of total portfolio equity in cash to avoid cash buffer overruns. |

---

## Key Components

### `FixedSignalsAlphaModel`
A built-in QSTrader `AlphaModel` that returns fixed target asset weight signals regardless of market conditions or price trends.

```python
strategy_alpha_model = FixedSignalsAlphaModel({'EQ:SPY': 0.6, 'EQ:AGG': 0.4})
```

### `StaticUniverse`
Defines a fixed asset universe for the duration of the backtest without dynamic asset additions or removals.

```python
strategy_universe = StaticUniverse(['EQ:SPY', 'EQ:AGG'])
```

### `CSVDailyBarDataSource` + `BacktestDataHandler`
Handles OHLCV bar data loading from CSV files. To optimize memory usage, `CSVDailyBarDataSource` is restricted via `csv_symbols=['SPY', 'AGG']` to only load data files for symbols required by the strategy.

```python
csv_dir = os.environ.get('QSTRADER_CSV_DATA_DIR', DATA_DIR)
data_source = CSVDailyBarDataSource(csv_dir, 'Equity', csv_symbols=strategy_symbols)
data_handler = BacktestDataHandler(strategy_universe, data_sources=[data_source])
```

### `BacktestTradingSession`
Orchestrates the event loop, broker simulation, portfolio tracking, rebalance scheduling, order execution, and equity curve recording.

```python
strategy_backtest = BacktestTradingSession(
    start_dt,
    end_dt,
    strategy_universe,
    strategy_alpha_model,
    rebalance='end_of_month',
    long_only=True,
    cash_buffer_percentage=0.01,
    data_handler=data_handler
)
strategy_backtest.run()
```

### `TearsheetStatistics`
Generates a visual performance tearsheet displaying strategy equity, benchmark equity, drawdowns, and summary performance statistics (CAGR, Sharpe ratio, Max Drawdown).

```python
tearsheet = TearsheetStatistics(
    strategy_equity=strategy_backtest.get_equity_curve(),
    benchmark_equity=benchmark_backtest.get_equity_curve(),
    title='60/40 US Equities/Bonds'
)
tearsheet.plot_results()
```

---

## Data Requirements

Place the following daily price CSV files in the QSTrader data directory (default: `data/` or path configured via `QSTRADER_CSV_DATA_DIR`):

- **`SPY.csv`**: Daily price data for SPDR S&P 500 ETF Trust.
- **`AGG.csv`**: Daily price data for iShares Core U.S. Aggregate Bond ETF.

Each CSV must contain daily open, high, low, close, volume, and adjusted close columns compatible with `CSVDailyBarDataSource`.

---

## How to Run

```bash
# From the repository root
python examples/sixty_forty.py
```

To specify a custom directory containing the CSV files:

```bash
QSTRADER_CSV_DATA_DIR=/path/to/your/csv/data python examples/sixty_forty.py
```

Upon execution, QSTrader runs the backtest event loops for both the strategy and benchmark and displays a Matplotlib tearsheet titled **"60/40 US Equities/Bonds"**.

---

## Output

The script outputs an interactive tearsheet plot featuring:

- **Equity Curve Comparison**: Growth of initial capital for the 60/40 portfolio versus 100% SPY.
- **Drawdown Chart**: Percentage peak-to-trough drawdowns for both curves over time.
- **Performance Summary Table**: Key statistics including CAGR, Sharpe Ratio, Sortino Ratio, Max Drawdown, and Monthly/Annualized volatility.

---

## Backtest Architecture

```
CSV Files (SPY.csv, AGG.csv)
    └─► CSVDailyBarDataSource (csv_symbols=['SPY', 'AGG'])
            └─► BacktestDataHandler
                    ├─► StaticUniverse (['EQ:SPY', 'EQ:AGG'])
                    ├─► FixedSignalsAlphaModel ({'EQ:SPY': 0.6, 'EQ:AGG': 0.4})
                    └─► BacktestTradingSession (end_of_month rebalance)
                                │
                                ├─► Strategy Equity Curve ──┐
                                │                           ├─► TearsheetStatistics
                                └─► Benchmark Equity Curve ─┘
```

---

## Notes

- **Zero Fee Model Baseline**: By default, `BacktestTradingSession` uses a `ZeroFeeModel`, providing an idealized, frictionless benchmark. To incorporate execution transaction fees and commissions, see `examples/sixty_forty_fees.py`.
- **Monthly Rebalancing Mechanism**: At the end of each calendar month, price drift will have shifted the asset weights away from 60/40. Rebalancing liquidates overperforming assets and buys underperforming assets to return portfolio allocation to target 60/40 ratios.
- **Cash Buffer**: The 1% cash buffer ensures that rounding during order sizing or minor intraday price movements will not result in negative cash balances or order rejections.

