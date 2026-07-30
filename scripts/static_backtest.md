# `scripts/static_backtest.py`

## Overview

`scripts/static_backtest.py` is a Command-Line Interface (CLI) tool built with `click` for running backtests on **fixed-allocation static portfolios** (rebalanced monthly) and comparing their performance against a benchmark portfolio (60/40 US Equities/Bonds: `SPY`/`AGG`).

---

## Features & Functionality

1. **Command-Line Interface (`click`):**
   - Configurable options for start/end dates, asset allocations, strategy title, strategy ID, and tearsheet rendering.

2. **Allocation String Parsing (`obtain_allocations`):**
   - Converts key-value allocation strings (e.g. `"SPY:0.6,AGG:0.4"`) into QSTrader's internal symbol format (`{'EQ:SPY': 0.6, 'EQ:AGG': 0.4}`).

3. **Strategy Backtest Execution:**
   - Constructs a `StaticUniverse` and loads pricing data via `CSVDailyBarDataSource` from `QSTRADER_CSV_DATA_DIR` or `qstrader.constants.DATA_DIR`.
   - Utilizes `FixedSignalsAlphaModel` with monthly rebalancing (`rebalance='end_of_month'`), long-only order sizing, and a 1% cash buffer.

4. **Benchmark Comparison:**
   - Automatically runs a parallel backtest across the same date range using a standard 60/40 US Equities/Bonds benchmark (`SPY`: 0.6, `AGG`: 0.4).

5. **Statistics Export & Tearsheet Visualization:**
   - Serializes backtest metrics (equity curves, CAGR, Sharpe ratio, max drawdown, target allocations) into JSON files (`<strat_id>_monthly.json`) via `JSONStatistics`.
   - Optionally renders interactive Matplotlib performance tearsheets via `TearsheetStatistics` when `--tearsheet` is passed.

---

## Command-Line Arguments

| Option | Argument | Description |
| :--- | :--- | :--- |
| `--start-date` | `start_date` | Backtest starting date (e.g. `2015-01-01`). |
| `--end-date` | `end_date` | Backtest ending date (e.g. `2020-12-31`). Defaults to yesterday's date if omitted. |
| `--allocations` | `allocations` | Comma-separated asset weights string (e.g. `"SPY:0.6,AGG:0.4"`). |
| `--title` | `strat_title` | Descriptive title/name for the backtest strategy. |
| `--id` | `strat_id` | Strategy ID string used for generating the output JSON filename (`<strat_id>_monthly.json`). |
| `--tearsheet` | `tearsheet` | Flag (`is_flag=True`) to render interactive performance tearsheet plots upon completion. |

---

## Usage Example

```bash
python scripts/static_backtest.py \
  --start-date 2015-01-01 \
  --end-date 2020-12-31 \
  --allocations "SPY:0.4,TLT:0.3,GLD:0.3" \
  --title "3-Asset Asset Allocation" \
  --id "three-asset" \
  --tearsheet
```

