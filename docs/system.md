# `qstrader.system`

## Overview

The `qstrader.system` package contains high-level **trading system wiring and rebalancing schedule abstractions**. It brings together portfolio construction, order execution handling, and rebalancing timelines.

The package consists of two primary parts:

- **Quantitative Trading System (`qts.py`):** `QuantTradingSystem` acts as the primary pipeline component that links signal models (`AlphaModel`, `RiskModel`), portfolio construction (`PortfolioConstructionModel`, `OrderSizer`, `PortfolioOptimiser`), and execution (`ExecutionHandler`, `MarketOrderExecutionAlgorithm`).
- **Rebalance Schedule Generators (`qstrader/system/rebalance/`):** Abstractions (`Rebalance`) and concrete schedule generators (`BuyAndHoldRebalance`, `DailyRebalance`, `WeeklyRebalance`, `EndOfMonthRebalance`) for determining exact timestamps when strategy rebalancing occurs.

---

## Package layout

```text
qstrader/system/
├── __init__.py
├── qts.py
└── rebalance/
    ├── __init__.py
    ├── buy_and_hold.py
    ├── daily.py
    ├── end_of_month.py
    ├── rebalance.py
    └── weekly.py
```

`qstrader/system/__init__.py` and `qstrader/system/rebalance/__init__.py` are empty, so imports are typically made directly from module paths.

---

## Core abstractions

### `QuantTradingSystem`

**Source:** `qstrader/system/qts.py`

`QuantTradingSystem` is a callable wrapper that encapsulates model setup, portfolio construction, and execution routing for a quantitative strategy.

#### Constructor

```python
def __init__(
    self,
    universe: Universe,
    broker: Broker,
    broker_portfolio_id: str,
    data_handler: BacktestDataHandler,
    alpha_model: AlphaModel,
    *args,
    risk_model: AlphaModel | None = None,
    long_only: bool = False,
    submit_orders: bool = False,
    **kwargs
)
```

#### Parameters

- `universe`: `Universe` instance specifying available assets.
- `broker`: `Broker` instance used for portfolio tracking and order submission.
- `broker_portfolio_id`: Specific broker portfolio ID to execute against.
- `data_handler`: `BacktestDataHandler` supplying asset market prices.
- `alpha_model`: `AlphaModel` generating signal forecasts.
- `risk_model`: Optional `AlphaModel` or `RiskModel` adjusting signal weights.
- `long_only`: Boolean flag indicating whether to instantiate `DollarWeightedCashBufferedOrderSizer` (`True`) or `LongShortLeveragedOrderSizer` (`False`; default).
- `submit_orders`: Boolean flag indicating whether orders should be sent to the broker (`True`) or held without submission (`False`).
- `**kwargs`: Configuration parameters passed to order sizers:
  - Required if `long_only=True`: `cash_buffer_percentage` (e.g. `0.05`).
  - Required if `long_only=False`: `gross_leverage` (e.g. `1.0`).

#### Callable Execution Pipeline

```python
def __call__(self, dt: pd.Timestamp, stats: dict | None = None) -> None
```

When invoked at timestamp `dt`:

1. **Portfolio Construction:** Executes `self.portfolio_construction_model(dt, stats=stats)`. Alpha and risk models are evaluated, target weights are optimized and sized into integer unit quantities, and rebalancing `Order` objects are generated.
2. **Order Execution:** Passes generated orders to `self.execution_handler(dt, rebalance_orders)`, which converts orders into executed transactions (or submits them to live/simulated brokers).

---

## Rebalancing Schedule Models

### `Rebalance`

**Source:** `qstrader/system/rebalance/rebalance.py`

Abstract base class for all rebalancing schedule generators.

#### Abstract Interface

```python
class Rebalance(object):
    @abstractmethod
    def output_rebalances(self):
        raise NotImplementedError("Should implement output_rebalances()")
```

Derived classes populate `self.rebalances`, a list of UTC `pd.Timestamp` objects indicating exact rebalance execution times.

---

### `BuyAndHoldRebalance`

**Source:** `qstrader/system/rebalance/buy_and_hold.py`

Generates a single rebalance timestamp at the start date (or the immediate next business day if the start date falls on a weekend).

#### Constructor

```python
def __init__(self, start_dt: pd.Timestamp)
```

- `start_dt`: Starting timestamp for the buy-and-hold strategy.

---

### `DailyRebalance`

**Source:** `qstrader/system/rebalance/daily.py`

Generates daily rebalance timestamps for every business day (Monday through Friday) between start and end dates.

#### Constructor

```python
def __init__(
    self,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    pre_market: bool = False
)
```

- `start_date`: Starting range timestamp.
- `end_date`: Ending range timestamp.
- `pre_market`: If `True`, sets rebalance time to market open (`14:30:00` UTC). If `False` (default), sets rebalance time to market close (`21:00:00` UTC).

---

### `WeeklyRebalance`

**Source:** `qstrader/system/rebalance/weekly.py`

Generates weekly rebalance timestamps for a specific day of the week between start and end dates.

#### Constructor

```python
def __init__(
    self,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    weekday: str,
    pre_market: bool = False
)
```

- `start_date`: Starting range timestamp.
- `end_date`: Ending range timestamp.
- `weekday`: Three-letter weekday code (`'MON'`, `'TUE'`, `'WED'`, `'THU'`, or `'FRI'`).
- `pre_market`: If `True`, sets rebalance time to market open (`14:30:00` UTC). If `False` (default), sets rebalance time to market close (`21:00:00` UTC).

---

### `EndOfMonthRebalance`

**Source:** `qstrader/system/rebalance/end_of_month.py`

Generates rebalance timestamps for the last business day of each month (`freq='BME'`).

#### Constructor

```python
def __init__(
    self,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
    pre_market: bool = False
)
```

- `start_dt`: Starting range timestamp.
- `end_dt`: Ending range timestamp.
- `pre_market`: If `True`, sets rebalance time to market open (`14:30:00` UTC). If `False` (default), sets rebalance time to market close (`21:00:00` UTC).

---

## Architecture & System Workflow Diagram

```text
                      +-----------------------------+
                      |   BacktestTradingSession    |
                      +--------------+--------------+
                                     |
                                     v (checks schedule)
                      +-----------------------------+
                      |      Rebalance Schedule     |
                      |   (e.g., WeeklyRebalance)   |
                      +--------------+--------------+
                                     | (if dt matches)
                                     v
                      +-----------------------------+
                      |    QuantTradingSystem(dt)   |
                      +--------------+--------------+
                                     |
        +----------------------------+----------------------------+
        |                                                         |
        v                                                         v
+-------------------------------+                     +-----------------------+
|  PortfolioConstructionModel   |                     |   ExecutionHandler    |
|  - AlphaModel                 |                     |  - MarketOrderAlgo    |
|  - RiskModel                  |   rebalance_orders  |  - Order Submission   |
|  - PortfolioOptimiser         |-------------------->|  - Broker Transact    |
|  - OrderSizer                 |                     +-----------------------+
+-------------------------------+
```

---

## Quick Reference Table

| Component | Module Path | Inputs / Parameters | Returns / Output |
| :--- | :--- | :--- | :--- |
| **`QuantTradingSystem`** | `qstrader.system.qts` | `universe`, `broker`, `portfolio_id`, `data_handler`, `alpha_model`, `risk_model`, `long_only`, `submit_orders`, `**kwargs` | `__call__(dt) -> None` |
| **`Rebalance`** | `qstrader.system.rebalance.rebalance` | Abstract Interface | Base interface for schedule generators |
| **`BuyAndHoldRebalance`** | `qstrader.system.rebalance.buy_and_hold` | `start_dt` | Single initial business day timestamp |
| **`DailyRebalance`** | `qstrader.system.rebalance.daily` | `start_date`, `end_date`, `pre_market=False` | Daily business day UTC timestamps |
| **`WeeklyRebalance`** | `qstrader.system.rebalance.weekly` | `start_date`, `end_date`, `weekday`, `pre_market=False` | Weekly UTC timestamps on specified weekday |
| **`EndOfMonthRebalance`** | `qstrader.system.rebalance.end_of_month` | `start_dt`, `end_dt`, `pre_market=False` | Business end-of-month UTC timestamps |

---

## Minimal Usage Example

```python
import pandas as pd
from qstrader.alpha_model.fixed_signals import FixedSignalsAlphaModel
from qstrader.system.qts import QuantTradingSystem
from qstrader.system.rebalance.weekly import WeeklyRebalance

# Define rebalance schedule
start_dt = pd.Timestamp("2020-01-01 00:00:00", tz="UTC")
end_dt = pd.Timestamp("2020-12-31 00:00:00", tz="UTC")

rebalance_schedule = WeeklyRebalance(start_dt, end_dt, weekday="WED", pre_market=False)

# Initialize strategy QTS
alpha_model = FixedSignalsAlphaModel({"SPY": 0.6, "TLT": 0.4})
qts = QuantTradingSystem(
    universe=universe,
    broker=broker,
    broker_portfolio_id="000001",
    data_handler=data_handler,
    alpha_model=alpha_model,
    long_only=True,
    cash_buffer_percentage=0.05,
    submit_orders=True
)

# Execute system at rebalance timestamp
rebalance_dt = rebalance_schedule.rebalances[0]
qts(rebalance_dt)
```

