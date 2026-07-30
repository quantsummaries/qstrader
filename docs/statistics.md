# `qstrader.statistics`

## Overview

The `qstrader.statistics` package provides performance calculation, statistical analysis, and strategy reporting tools for QSTrader backtests. It computes risk-adjusted metrics, drawdown statistics, and returns aggregations, and provides visual reporting (Matplotlib/Seaborn tearsheets) as well as structured data export (JSON files).

The package consists of four core components:

- **Performance Metrics (`performance.py`):** Standalone mathematical functions for CAGR, Sharpe ratio, Sortino ratio, drawdowns, and returns aggregation.
- **Abstract Interface (`statistics.py`):** `Statistics` abstract base class for performance tracking modules.
- **Tearsheet Reporting (`tearsheet.py`):** `TearsheetStatistics` subclass generating institutional-style visual "one-pager" performance reports.
- **JSON Data Export (`json_statistics.py`):** `JSONStatistics` standalone exporter serializing strategy statistics, benchmark comparisons, and target asset allocations to JSON for web dashboards or Highcharts visualizations.

---

## Package layout

```text
qstrader/statistics/
├── __init__.py
├── json_statistics.py
├── performance.py
├── statistics.py
└── tearsheet.py
```

`qstrader/statistics/__init__.py` is currently empty, so imports are made directly from the concrete module paths.

---

## Performance metrics (`performance.py`)

**Source:** `qstrader/statistics/performance.py`

`performance.py` contains standalone mathematical helper functions for portfolio performance and risk analysis.

### `aggregate_returns`

```python
aggregate_returns(returns: pd.Series, convert_to: str) -> pd.Series
```

Aggregates a Pandas Series of periodic percentage returns into coarser frequencies.

- `returns: pd.Series` — time series of periodic percentage returns.
- `convert_to: str` — aggregation frequency (`'weekly'`, `'monthly'`, or `'yearly'`).

#### Calculation

Compound returns within each grouping period are calculated as:

$$\text{Compound Return} = \exp\left(\sum \log(1 + r_i)\right) - 1$$

---

### `create_cagr`

```python
create_cagr(equity: pd.Series, periods: int=252) -> float
```

Calculates the Compound Annual Growth Rate (CAGR) based on an equity or cumulative returns curve.

- `equity: pd.Series` — time series of portfolio equity or cumulative returns.
- `periods: int = 252` — annualization scale factor (e.g. `252` for daily, `252 * 6.5` for hourly).

#### Calculation

$$\text{Years} = \frac{\text{len}(\text{equity})}{\text{periods}}$$

$$\text{CAGR} = \left(\text{equity}_{\text{final}}\right)^{\frac{1}{\text{Years}}} - 1.0$$

---

### `create_sharpe_ratio`

```python
create_sharpe_ratio(returns: pd.Series, periods: int=252) -> float
```

Calculates the annualized Sharpe ratio assuming a risk-free benchmark rate of zero.

- `returns: pd.Series` — time series of period percentage returns.
- `periods: int = 252` — annualization scale factor (`252` for daily).

#### Calculation

$$\text{Sharpe} = \sqrt{\text{periods}} \times \frac{\mu(r)}{\sigma(r)}$$

---

### `create_sortino_ratio`

```python
create_sortino_ratio(returns: pd.Series, periods: int=252) -> float
```

Calculates the annualized Sortino ratio using downside standard deviation (returns $< 0$) assuming a risk-free rate of zero.

- `returns: pd.Series` — time series of period percentage returns.
- `periods: int = 252` — annualization scale factor.

#### Calculation

$$\text{Sortino} = \sqrt{\text{periods}} \times \frac{\mu(r)}{\sigma(r_{\text{negative}})}$$

---

### `create_drawdowns`

```python
create_drawdowns(returns: pd.Series) -> tuple[pd.Series, float, int]
```

Calculates drawdown statistics from a cumulative returns time series.

- `returns: pd.Series` — time series of cumulative returns (e.g. starting at `1.0`).

#### Returns

1. `drawdown: pd.Series` — fractional underwater drawdown time series.
2. `max_drawdown: float` — maximum peak-to-trough drawdown percentage.
3. `duration: int` — maximum continuous duration (number of periods) spent in drawdown.

---

## Abstract interface (`statistics.py`)

### `Statistics`

**Source:** `qstrader/statistics/statistics.py`

Abstract base class specifying the contract for performance tracking and statistics objects.

```python
class Statistics(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def update(self, dt): ...

    @abstractmethod
    def get_results(self): ...

    @abstractmethod
    def plot_results(self): ...

    @abstractmethod
    def save(self, filename): ...
```

#### Abstract methods

- `update(dt)` — update internal statistics on simulation tick `dt`.
- `get_results()` — return dictionary containing calculated performance metrics.
- `plot_results()` — plot visual representation of collected performance.
- `save(filename)` — save statistics output to a file.

---

## Visual tearsheet reporting (`tearsheet.py`)

### `TearsheetStatistics`

**Source:** `qstrader/statistics/tearsheet.py`

Subclass of `Statistics` that generates a Matplotlib / Seaborn institutional strategy performance tearsheet ("one-pager").

#### Constructor

```python
TearsheetStatistics(
    strategy_equity: pd.DataFrame,
    benchmark_equity: pd.DataFrame|None=None,
    title: str|None=None,
    periods: int=252
)
```

#### Parameters

- `strategy_equity: pd.DataFrame` — strategy equity curve DataFrame with `Equity` column indexed by date.
- `benchmark_equity: pd.DataFrame | None = None` — optional benchmark equity curve DataFrame with `Equity` column.
- `title: str | None = None` — title printed at the top of the report figure.
- `periods: int = 252` — annualization periods (`252` for daily).

#### Methods

##### `get_results(equity_df: pd.DataFrame) -> dict`

Computes performance metrics from the equity DataFrame:
- `returns`: periodic percentage returns
- `cum_returns`: cumulative returns time series
- `sharpe`: annualized Sharpe ratio
- `drawdowns`: drawdown time series
- `max_drawdown`: maximum peak-to-trough drawdown
- `max_drawdown_duration`: duration of maximum drawdown in periods

##### `plot_results(filename: str|None=None) -> None`

Renders a 5-panel GridSpec visual report containing:
1. **Cumulative Returns Plot:** strategy vs. optional benchmark equity curves over time.
2. **Drawdown Area Chart:** underwater drawdown percentage curve over time.
3. **Monthly Returns Heatmap:** Seaborn annotated heatmap of monthly percentage returns (Jan–Dec).
4. **Yearly Returns Bar Chart:** bar chart of annual percentage returns.
5. **Summary Text Statistics Table:** side-by-side strategy and benchmark metrics (Total Return, CAGR, Sharpe, Sortino, Annual Volatility, Max Daily Drawdown, Max Drawdown Duration).

If `filename` is provided as a string, the figure is saved to that file before display.

---

## JSON statistics export (`json_statistics.py`)

### `JSONStatistics`

**Source:** `qstrader/statistics/json_statistics.py`

Standalone class that serializes backtest performance metrics, benchmark comparisons, and target asset allocations into a structured JSON file.

#### Constructor

```python
JSONStatistics(
    equity_curve: pd.DataFrame,
    target_allocations: pd.DataFrame,
    strategy_id: str|None=None,
    strategy_name: str|None=None,
    benchmark_curve: pd.DataFrame|None=None,
    benchmark_id: str|None=None,
    benchmark_name: str|None=None,
    periods: int=252,
    output_filename: str='statistics.json'
)
```

#### Parameters

- `equity_curve: pd.DataFrame` — strategy equity curve DataFrame (`Equity` column indexed by date).
- `target_allocations: pd.DataFrame` — target portfolio weights DataFrame indexed by date with asset symbols as columns.
- `strategy_id: str | None = None` — optional strategy identifier string.
- `strategy_name: str | None = None` — optional strategy display name string.
- `benchmark_curve: pd.DataFrame | None = None` — optional benchmark equity curve DataFrame.
- `benchmark_id: str | None = None` — optional benchmark identifier string.
- `benchmark_name: str | None = None` — optional benchmark display name string.
- `periods: int = 252` — annualization scaling factor.
- `output_filename: str = 'statistics.json'` — target JSON output path.

#### Methods

##### `to_file() -> None`

Writes the complete `self.statistics` dictionary to `output_filename` formatted as JSON.

#### JSON Data Structure

The output JSON contains structured keys for `'strategy'`, optional `'benchmark'`, and strategy/benchmark metadata:

```json
{
  "strategy_id": "60_40_strategy",
  "strategy_name": "60/40 US Equities/Bonds",
  "strategy": {
    "equity_curve": [[epoch_ms, value], ...],
    "returns": [[epoch_ms, return_val], ...],
    "cum_returns": [[epoch_ms, cum_val], ...],
    "monthly_agg_returns": [[["year", "month"], return_val], ...],
    "monthly_agg_returns_hc": [[month_idx, year_idx, pct_return], ...],
    "yearly_agg_returns": [[year, return_val], ...],
    "yearly_agg_returns_hc": [pct_return, ...],
    "returns_quantiles": {
      "daily": {"min": ..., "lq": ..., "med": ..., "uq": ..., "max": ...},
      "monthly": {"min": ..., "lq": ..., "med": ..., "uq": ..., "max": ...},
      "yearly": {"min": ..., "lq": ..., "med": ..., "uq": ..., "max": ...}
    },
    "returns_quantiles_hc": [[daily_box], [monthly_box], [yearly_box]],
    "drawdowns": [[epoch_ms, dd_pct], ...],
    "max_drawdown": 0.1234,
    "max_drawdown_duration": 45,
    "mean_returns": 0.0004,
    "stdev_returns": 0.0082,
    "cagr": 0.085,
    "annualised_vol": 0.130,
    "sharpe": 0.65,
    "sortino": 0.92,
    "target_allocations": [
      {"name": "SPY", "data": [[epoch_ms, weight], ...]}
    ]
  }
}
```

*Note: Keys ending in `_hc` contain formatting optimized for direct ingestion by Highcharts graphics components.*

---

## How statistics are used in QSTrader

### 1. BacktestTradingSession helper methods

`BacktestTradingSession` in `qstrader/trading/backtest.py` provides convenience methods to extract data structures required by `TearsheetStatistics` and `JSONStatistics`:

- `get_equity_curve() -> pd.DataFrame` — returns DataFrame with `Equity` column indexed by date.
- `get_target_allocations() -> pd.DataFrame` — returns DataFrame of target asset weights indexed by date.

### 2. Strategy examples and scripts

Repository examples (`examples/sixty_forty.py`, `examples/sixty_forty_fees.py`, `examples/long_short.py`, `examples/momentum_taa.py`, and `scripts/static_backtest.py`) construct tearsheets as follows:

```python
# Run backtest
backtest = BacktestTradingSession(...)
backtest.run(results=False)

# Extract equity curve
equity_curve = backtest.get_equity_curve()

# Display tearsheet
tearsheet = TearsheetStatistics(
    strategy_equity=equity_curve,
    title='60/40 US Equities/Bonds Strategy'
)
tearsheet.plot_results()
```

---

## Design notes and limitations

- **Zero Risk-Free Rate:** Sharpe and Sortino ratios currently assume a risk-free rate of zero.
- **Daily Annualization:** Default period scaling is `periods=252` (daily business days).
- **Highcharts Data Helpers:** `JSONStatistics` contains static and helper methods (`_hc` suffixes) specifically tailored for Highcharts web charting.
- **Package `__init__.py`:** `qstrader/statistics/__init__.py` is currently empty; modules must be imported from concrete submodules.

---

## Quick reference

| Class / Function | Module | Purpose | Key API |
|---|---|---|---|
| `aggregate_returns` | `qstrader.statistics.performance` | Aggregate periodic returns | `aggregate_returns(returns, convert_to='monthly')` |
| `create_cagr` | `qstrader.statistics.performance` | Calculate CAGR | `create_cagr(equity, periods=252) -> float` |
| `create_sharpe_ratio` | `qstrader.statistics.performance` | Calculate Sharpe ratio | `create_sharpe_ratio(returns, periods=252) -> float` |
| `create_sortino_ratio` | `qstrader.statistics.performance` | Calculate Sortino ratio | `create_sortino_ratio(returns, periods=252) -> float` |
| `create_drawdowns` | `qstrader.statistics.performance` | Calculate drawdowns & duration | `create_drawdowns(returns) -> (drawdown_s, max_dd, dd_dur)` |
| `Statistics` | `qstrader.statistics.statistics` | Abstract statistics interface | `update`, `get_results`, `plot_results`, `save` |
| `TearsheetStatistics` | `qstrader.statistics.tearsheet` | Matplotlib performance report | `TearsheetStatistics(strategy_equity, title=...).plot_results(filename=None)` |
| `JSONStatistics` | `qstrader.statistics.json_statistics` | Export backtest stats to JSON | `JSONStatistics(equity_curve, target_allocations, ...).to_file()` |

---

## Minimal usage examples

### Computing performance metrics directly

```python
import pandas as pd
from qstrader.statistics.performance import (
    create_cagr, create_sharpe_ratio, create_sortino_ratio, create_drawdowns
)

equity_series = pd.Series([100.0, 102.0, 101.5, 105.0, 108.0])
returns_series = equity_series.pct_change().fillna(0.0)

cagr = create_cagr(equity_series, periods=252)
sharpe = create_sharpe_ratio(returns_series, periods=252)
sortino = create_sortino_ratio(returns_series, periods=252)
dd_s, max_dd, max_dd_duration = create_drawdowns(equity_series)

print(f"CAGR: {cagr:.2%}, Sharpe: {sharpe:.2f}, Max DD: {max_dd:.2%}")
```

### Exporting backtest results to JSON

```python
from qstrader.statistics.json_statistics import JSONStatistics

equity_curve = backtest.get_equity_curve()
target_allocations = backtest.get_target_allocations()

json_stats = JSONStatistics(
    equity_curve=equity_curve,
    target_allocations=target_allocations,
    strategy_id='my_strategy_001',
    strategy_name='My Custom Momentum Strategy',
    output_filename='output_stats.json'
)
json_stats.to_file()
```

---

## Summary

`qstrader.statistics` provides performance analysis and reporting for QSTrader backtests. It offers robust performance metrics in `performance.py`, institutional visual reporting through `TearsheetStatistics`, and structured JSON exports for web interfaces via `JSONStatistics`.

