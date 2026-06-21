# `qstrader.trading`

## Overview

The `qstrader.trading` package provides top-level **session management and backtest orchestration** for QSTrader. It encapsulates the complete simulation environment, bringing together data ingestion, exchange calendars, broker simulation, strategy signal generation, rebalancing schedules, and performance tracking into a single unified engine.

Key abstractions in the package include:

- **Trading Session Interface (`trading_session.py`):** `TradingSession` abstract base class defining the contract for live and backtested trading sessions.
- **Backtest Session Orchestrator (`backtest.py`):** `BacktestTradingSession` concrete trading session that wires together all QSTrader subsystems and manages event iteration from start to end timestamps.

---

## Package layout

```text
qstrader/trading/
├── __init__.py
├── backtest.py
└── trading_session.py
```

`qstrader/trading/__init__.py` is currently empty, so imports are typically made directly from module paths (e.g. `from qstrader.trading.backtest import BacktestTradingSession`).

---

## Core abstractions

### `TradingSession`

**Source:** `qstrader/trading/trading_session.py`

`TradingSession` is the abstract base class for all live and backtested execution environments in QSTrader.

#### Abstract Interface

```python
class TradingSession(object):
    @abstractmethod
    def run(self):
        raise NotImplementedError("Should implement run()")
```

Subclasses implement `run()` to execute the main event loop.

---

### `BacktestTradingSession`

**Source:** `qstrader/trading/backtest.py`

`BacktestTradingSession` is the primary top-level entry point for running quantitative trading strategy backtests. It automates component instantiation and event loop iteration over historical data.

#### Constants

- `DEFAULT_ACCOUNT_NAME`: `'Backtest Simulated Broker Account'`
- `DEFAULT_PORTFOLIO_ID`: `'000001'`
- `DEFAULT_PORTFOLIO_NAME`: `'Backtest Simulated Broker Portfolio'`

#### Constructor

```python
def __init__(
    self,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
    universe: Universe,
    alpha_model: AlphaModel,
    risk_model: RiskModel | None = None,
    signals: SignalsCollection | None = None,
    initial_cash: float = 1e6,
    rebalance: str = 'weekly',
    account_name: str = DEFAULT_ACCOUNT_NAME,
    portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    portfolio_name: str = DEFAULT_PORTFOLIO_NAME,
    long_only: bool = False,
    fee_model: FeeModel = ZeroFeeModel(),
    burn_in_dt: pd.Timestamp | None = None,
    data_handler: BacktestDataHandler | None = None,
    **kwargs
)
```

#### Parameters

- `start_dt`: Starting datetime (UTC) of the backtest simulation.
- `end_dt`: Ending datetime (UTC) of the backtest simulation.
- `universe`: `Universe` instance specifying assets available to trade.
- `alpha_model`: `AlphaModel` generating raw signal forecasts.
- `risk_model`: Optional `RiskModel` for portfolio risk adjustments.
- `signals`: Optional `SignalsCollection` containing rolling signal buffers (e.g. SMA, Momentum) updated daily on market close.
- `initial_cash`: Starting capital in broker cash account (default `$1,000,000`).
- `rebalance`: Rebalancing frequency string (`'daily'`, `'weekly'`, `'end_of_month'`, or `'buy_and_hold'`; default `'weekly'`).
- `account_name`: ID string for simulated broker account.
- `portfolio_id`: ID string for portfolio created at simulated broker.
- `portfolio_name`: Display name for portfolio.
- `long_only`: Boolean flag indicating whether strategy is long-only (`True`) or long/short leveraged (`False`; default).
- `fee_model`: `FeeModel` instance used for transaction cost calculations (default `ZeroFeeModel()`).
- `burn_in_dt`: Optional warm-up timestamp. Statistics and equity logging begin on or after this timestamp.
- `data_handler`: Optional `BacktestDataHandler`. If omitted, defaults to `CSVDailyBarDataSource` configured via environment variable `QSTRADER_CSV_DATA_DIR` or current working directory.
- `**kwargs`: Required keyword arguments based on session configuration:
  - `rebalance_weekday`: Required when `rebalance='weekly'` (e.g. `'MON'`, `'WED'`, `'FRI'`).
  - `cash_buffer_percentage`: Required when `long_only=True` (e.g. `0.05`).
  - `gross_leverage`: Required when `long_only=False` (e.g. `1.0` or `1.5`).

---

## Session Execution Loop

Calling `run(results=False)` executes the full simulation event loop:

```python
def run(self, results: bool = False) -> None
```

```text
               +-------------------------------+
               |  DailyBusinessDaySimulation   |
               |            Engine             |
               +---------------+---------------+
                               |
                               v (yields SimulationEvent)
               +---------------+---------------+
               |     BacktestTradingSession    |
               +---------------+---------------+
                               |
       +-----------------------+-----------------------+
       |                       |                       |
       v                       v                       v
1. Broker Update      2. Signal Update         3. Strategy Rebalance
 (broker.update)      (signals.update)            (qts(dt))
 [On every event]    [On market_close]         [On rebalance dates]
       |                       |                       |
       +-----------------------+-----------------------+
                               |
                               v
                      4. Equity Tracking
                    (_update_equity_curve)
                     [On market_close]
```

### Event Loop Logic

1. **Broker Update:** `self.broker.update(dt)` processes market orders, updates current portfolio asset prices, and transacts execution trades.
2. **Signal Update:** On `market_close` events, if `signals` is provided, invokes `self.signals.update(dt)` to append latest price bars into lookback buffers.
3. **Rebalancing & Execution:** If `dt` matches the rebalance schedule (and `dt >= burn_in_dt`), calls `self.qts(dt, stats=stats)`. The `QuantTradingSystem` evaluates alpha/risk models, optimizes target weights, sizes order quantities, and submits trade orders to the broker.
4. **Equity Curve Tracking:** On `market_close` events (and `dt >= burn_in_dt`), appends current total account equity to `self.equity_curve`.
5. **Post-Simulation Output:** At loop completion, stores target allocations and optionally calls `output_holdings()` if `results=True`.

---

## Data Analysis & Export Methods

### `get_equity_curve()`

```python
def get_equity_curve(self) -> pd.DataFrame
```

Returns a Pandas DataFrame with a date index (`datetime.date`) and an `'Equity'` column tracking daily portfolio value over time.

In QSTrader, total account equity at timestamp `dt` is recorded at market close as:

$$\text{Total Equity} = \text{Cash} + \text{Total Market Value}$$

where:
* **Cash**: Settled account cash remaining after accounting for buys, sells, commissions, fees, and taxes.
* **Total Market Value**: Sum of mark-to-market values across all active asset positions ($\sum Q_i \times P_i$).

### `get_target_allocations()`

```python
def get_target_allocations(self) -> pd.DataFrame
```

Returns a Pandas DataFrame with a date index matching the equity curve and asset columns containing forward-filled target portfolio weight allocations.

### `output_holdings()`

```python
def output_holdings(self) -> None
```

Prints formatted current holdings and total account equity to console.

---

## Quick Reference Table

| Method / Property | Signature / Type | Description |
| :--- | :--- | :--- |
| **`__init__`** | `(start_dt, end_dt, universe, alpha_model, ...)` | Initializes exchange, data handler, broker, sim engine, rebalance schedule, and QTS. |
| **`run`** | `(results: bool = False) -> None` | Executes full backtest event loop. |
| **`get_equity_curve`** | `() -> pd.DataFrame` | Returns date-indexed DataFrame with strategy portfolio value. |
| **`get_target_allocations`** | `() -> pd.DataFrame` | Returns date-indexed DataFrame of target weights per asset. |
| **`output_holdings`** | `() -> None` | Prints position breakdown to stdout. |

---

## Minimal Usage Example

```python
import pandas as pd
from qstrader.alpha_model.fixed_signals import FixedSignalsAlphaModel
from qstrader.asset.equity import Equity
from qstrader.asset.universe.static import StaticUniverse
from qstrader.trading.backtest import BacktestTradingSession

# Define date range and asset universe
start_dt = pd.Timestamp("2020-01-01 00:00:00", tz="UTC")
end_dt = pd.Timestamp("2020-12-31 00:00:00", tz="UTC")

assets = [Equity("SPY", "SPY"), Equity("TLT", "TLT")]
universe = StaticUniverse(assets)

# Define 60/40 static asset weight signal model
alpha_model = FixedSignalsAlphaModel({"SPY": 0.60, "TLT": 0.40})

# Construct backtest session
backtest = BacktestTradingSession(
    start_dt=start_dt,
    end_dt=end_dt,
    universe=universe,
    alpha_model=alpha_model,
    rebalance="weekly",
    rebalance_weekday="WED",
    long_only=True,
    cash_buffer_percentage=0.02,
    initial_cash=100000.0
)

# Run simulation
backtest.run(results=True)

# Retrieve results
equity_curve = backtest.get_equity_curve()
target_allocs = backtest.get_target_allocations()
```

