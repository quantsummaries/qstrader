# 60/40 US Equities/Bonds Portfolio With Fees — `sixty_forty_fees.py`

## Overview

This example extends the classic **60/40 Multi-Asset Portfolio** by incorporating explicit **transaction fees, commissions, and taxes** using QSTrader's `PercentFeeModel`. 

Unlike `sixty_forty.py` (which compares a 60/40 portfolio against a buy-and-hold SPY benchmark), this backtest compares:
1. **Strategy (With Fees)**: A 60% `SPY` / 40% `AGG` monthly-rebalanced portfolio subject to transaction fees and taxes (`PercentFeeModel`).
2. **Benchmark (Friction-Free Baseline)**: The exact same 60% `SPY` / 40% `AGG` monthly-rebalanced portfolio with zero transaction fees (`ZeroFeeModel`).

This comparison directly isolates the net drag of trade execution costs and financial transaction taxes on long-term rebalanced portfolio performance.

---

## Strategy Logic

1. **Universe** — `StaticUniverse` consisting of `EQ:SPY` (S&P 500 ETF) and `EQ:AGG` (iShares Core U.S. Aggregate Bond ETF).
2. **Alpha Model (`FixedSignalsAlphaModel`)** — Assigns static target weights at every monthly rebalance:
   - `EQ:SPY`: **0.60** (60%)
   - `EQ:AGG`: **0.40** (40%)
3. **Transaction Fee Model (`PercentFeeModel`)**:
   - `commission_pct`: `0.1 / 100.0` (0.10% or 10 bps per trade order value).
   - `tax_pct`: `0.5 / 100.0` (0.50% or 50 bps financial transaction tax / stamp duty per trade order value).
   - Total friction per trade fill: **0.60%** of gross transaction value.
4. **Rebalance Schedule** — `end_of_month` (triggers rebalancing on the final business day of each calendar month).
5. **Benchmark** — An identical 60/40 monthly-rebalanced portfolio instantiated with `fee_model=ZeroFeeModel()`.

---

## Parameters

| Parameter | Value | Description |
|---|---|---|
| `start_dt` | `2003-09-30 14:30:00 UTC` | Start date of the backtest simulation. |
| `end_dt` | `2019-12-31 23:59:00 UTC` | End date of the backtest simulation. |
| `strategy_symbols` | `['SPY', 'AGG']` | Ticker symbols representing the strategy assets. |
| `commission_pct` | `0.0010` (0.10%) | Percentage commission charged by broker on filled transactions. |
| `tax_pct` | `0.0050` (0.50%) | Percentage transaction tax / stamp duty applied to filled transactions. |
| `rebalance` | `'end_of_month'` | Rebalances weights on the final business day of every month. |
| `long_only` | `True` | Restricts portfolio holdings to long positions only. |
| `cash_buffer_percentage` | `0.01` | Retains 1% cash buffer to accommodate fee deductions without negative cash balances. |

---

## Key Components

### `PercentFeeModel`
Calculates execution costs for every executed trade fill based on fixed percentage rates for commissions and transaction taxes:

$$\text{Total Fee} = \text{Order Consideration} \times (\text{commission\_pct} + \text{tax\_pct})$$

In this example:
```python
fee_model = PercentFeeModel(commission_pct=0.1 / 100.0, tax_pct=0.5 / 100.0)
```

### `ZeroFeeModel`
Provides a zero-cost execution model used by the benchmark session to represent ideal, friction-free trading:

```python
benchmark_backtest = BacktestTradingSession(
    start_dt,
    end_dt,
    strategy_universe,
    strategy_alpha_model,
    rebalance='end_of_month',
    long_only=True,
    cash_buffer_percentage=0.01,
    data_handler=data_handler,
    fee_model=ZeroFeeModel()
)
```

### `BacktestTradingSession` (Strategy with Fees)
Applies `fee_model` to deduct commissions and taxes directly from account cash whenever trades are filled:

```python
strategy_backtest = BacktestTradingSession(
    start_dt,
    end_dt,
    strategy_universe,
    strategy_alpha_model,
    rebalance='end_of_month',
    long_only=True,
    cash_buffer_percentage=0.01,
    data_handler=data_handler,
    fee_model=fee_model
)
strategy_backtest.run()
```

### `TearsheetStatistics`
Renders performance metrics and plots the equity curves of the fee-adjusted strategy against the fee-free baseline under the title **"60/40 US Equities/Bonds (With/Without Fees)"**.

```python
tearsheet = TearsheetStatistics(
    strategy_equity=strategy_backtest.get_equity_curve(),
    benchmark_equity=benchmark_backtest.get_equity_curve(),
    title='60/40 US Equities/Bonds (With/Without Fees)'
)
tearsheet.plot_results()
```

---

## Data Requirements

Place the following daily price CSV files in the QSTrader data directory (default: `data/` or path configured via `QSTRADER_CSV_DATA_DIR`):

- **`SPY.csv`**: Daily price data for SPDR S&P 500 ETF Trust.
- **`AGG.csv`**: Daily price data for iShares Core U.S. Aggregate Bond ETF.

Each CSV file must contain daily OHLCV bar data compatible with `CSVDailyBarDataSource`.

---

## How to Run

```bash
# From the repository root
python examples/sixty_forty_fees.py
```

To use a custom directory containing the CSV files:

```bash
QSTRADER_CSV_DATA_DIR=/path/to/your/csv/data python examples/sixty_forty_fees.py
```

Upon completion, QSTrader displays a Matplotlib tearsheet titled **"60/40 US Equities/Bonds (With/Without Fees)"**.

---

## Output

The interactive tearsheet plot includes:

- **Fee Drag Visualization**: Displays the widening gap over time between the fee-adjusted equity curve and the friction-free benchmark curve.
- **Drawdown Analysis**: Compares max drawdown and recovery times with and without transaction costs.
- **Performance Summary Table**: Displays metrics such as net CAGR, Sharpe ratio, and total returns after deducting transaction costs.

---

## Backtest Architecture

```
CSV Files (SPY.csv, AGG.csv)
    └─► CSVDailyBarDataSource
            └─► BacktestDataHandler
                    ├─► StaticUniverse (['EQ:SPY', 'EQ:AGG'])
                    ├─► FixedSignalsAlphaModel ({'EQ:SPY': 0.6, 'EQ:AGG': 0.4})
                    │
                    ├─► BacktestTradingSession (PercentFeeModel) ──► Fee Equity Curve ──┐
                    │                                                                   ├─► TearsheetStatistics
                    └─► BacktestTradingSession (ZeroFeeModel)    ──► Zero Fee Curve ──┘
```

---

## Notes & Takeaways

- **Impact of Rebalance Frequency**: Monthly rebalancing triggers transactions 12 times a year. When total transaction costs (commission + tax) equal 0.60% per trade, compounding fee deductions lead to a noticeable performance drag over a multi-year horizon.
- **Cash Buffer Management**: Retaining `cash_buffer_percentage=0.01` ensures the account has adequate cash to pay for fee deductions upon fill execution without triggering negative cash errors.
- **Isolating Friction Costs**: Setting up two identical `BacktestTradingSession` instances (differing only by `fee_model`) provides a controlled experiment for measuring transaction cost sensitivity in quantitative trading strategies.

