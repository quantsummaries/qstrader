# `qstrader.simulation`

## Overview

The `qstrader.simulation` package provides the **event-loop clock and timeline engine** for QSTrader backtests. It controls the progression of time throughout a simulation by yielding timestamped event objects representing market session milestones (e.g. pre-market, market open, market close, post-market).

The package is built around three core abstractions:

- **Base Simulation Interface (`sim_engine.py`):** `SimulationEngine` abstract base class defining the generator contract (`__iter__`).
- **Simulation Event Container (`event.py`):** `SimulationEvent` value object encapsulating a timestamp and event type string.
- **Daily Business-Day Engine (`daily_bday.py`):** `DailyBusinessDaySimulationEngine` concrete generator yielding daily market events for business days (Monday–Friday).

---

## Package layout

```text
qstrader/simulation/
├── __init__.py
├── daily_bday.py
├── event.py
└── sim_engine.py
```

`qstrader/simulation/__init__.py` is currently empty, so imports are typically made directly from concrete module paths.

---

## Core abstractions

### `SimulationEngine`

**Source:** `qstrader/simulation/sim_engine.py`

`SimulationEngine` is the abstract base class for all simulation time/event generators.

```python
class SimulationEngine(object):
    @abstractmethod
    def __iter__(self):
        raise NotImplementedError("Should implement __iter__()")
```

#### Contract

Subclasses must override `__iter__` to yield `SimulationEvent` instances in chronological order. Each yielded event signals a time tick in the simulation loop.

#### Design intent

This abstraction decouples strategy time-stepping from the rest of the backtesting system, enabling different simulation resolutions (e.g., daily business days, intraday bars, or tick-level data) without modifying strategy or broker execution code.

---

### `SimulationEvent`

**Source:** `qstrader/simulation/event.py`

`SimulationEvent` is an immutable value object representing a point in time and event category during a simulation.

#### Constructor

```python
SimulationEvent(ts: pd.Timestamp, event_type: str)
```

#### Parameters

- `ts: pd.Timestamp` — timezone-aware timestamp of the simulation event.
- `event_type: str` — string identifier for the event type (e.g. `'pre_market'`, `'market_open'`, `'market_close'`, `'post_market'`).

#### Attributes

- `ts: pd.Timestamp` — event timestamp.
- `event_type: str` — event category string.

#### Methods

- `__eq__(rhs: SimulationEvent) -> bool` — returns `True` if both `ts` and `event_type` match between two `SimulationEvent` instances.

---

## Daily business day simulation engine (`daily_bday.py`)

### `DailyBusinessDaySimulationEngine`

**Source:** `qstrader/simulation/daily_bday.py`

`DailyBusinessDaySimulationEngine` inherits from `SimulationEngine` and generates market events on standard business days (Monday to Friday).

#### Constructor

```python
DailyBusinessDaySimulationEngine(
    starting_day: pd.Timestamp,
    ending_day: pd.Timestamp,
    pre_market: bool = True,
    post_market: bool = True
)
```

#### Parameters

- `starting_day: pd.Timestamp` — start timestamp of the simulation.
- `ending_day: pd.Timestamp` — end timestamp of the simulation. Must be $\ge$ `starting_day` (raises `ValueError` otherwise).
- `pre_market: bool = True` — whether to generate `pre_market` events.
- `post_market: bool = True` — whether to generate `post_market` events.

#### Event timeline per business day

For every business day generated via `pandas.tseries.offsets.BDay()`, the engine yields events at the following fixed UTC times:

| Order | Event Type | UTC Time | Enabled Condition | Purpose |
|---|---|---|---|---|
| 1 | `pre_market` | `00:00:00` | `pre_market=True` | Cash subscriptions, corporate action processing |
| 2 | `market_open` | `14:30:00` | Always | Exchange open, pending order execution |
| 3 | `market_close` | `21:00:00` | Always | Exchange close, daily portfolio valuation |
| 4 | `post_market` | `23:59:00` | `post_market=True` | End-of-day rebalance logic & statistics collection |

---

## How simulation engines are used in QSTrader

### 1. Backtest session setup

`BacktestTradingSession` in `qstrader/trading/backtest.py` initializes a `DailyBusinessDaySimulationEngine` during setup:

```python
def _create_sim_engine(self):
    return DailyBusinessDaySimulationEngine(
        self.start_dt,
        self.end_dt,
        pre_market=True,
        post_market=True
    )
```

### 2. Main simulation event loop

During `BacktestTradingSession.run()`, the trading session iterates through `self.sim_engine`:

```python
for event in self.sim_engine:
    dt = event.ts
    if event.event_type == 'market_open':
        self.broker.update(dt)
    elif event.event_type == 'market_close':
        self.broker.update(dt)
    elif event.event_type == 'post_market':
        # Rebalance strategy logic, order generation, and equity tracking
        self.qts(dt)
```

---

## Observed test coverage

Unit tests in `tests/unit/simulation/` cover both classes:

- `test_event.py`: verifies `SimulationEvent.__eq__` across matching and non-matching timestamps and event types.
- `test_daily_bday.py`: verifies that `DailyBusinessDaySimulationEngine` correctly skips weekends (e.g. 2020-01-04 and 2020-01-05) and yields the exact expected sequence of timestamps and event types with `pre_market` / `post_market` flags enabled or disabled.

---

## Design notes and limitations

- **Hardcoded UTC Intraday Times:** `market_open` (14:30 UTC) and `market_close` (21:00 UTC) are hardcoded to match US equity market hours.
- **No Regional Holidays:** Uses `pandas.tseries.offsets.BDay()`, which filters out weekends but does not account for statutory/federal holidays.
- **Extensibility:** Custom timeline resolutions (e.g. intraday, multi-exchange schedules) can be created by implementing new subclasses of `SimulationEngine`.

---

## Quick reference

| Class | Module | Purpose | Key API |
|---|---|---|---|
| `SimulationEngine` | `qstrader.simulation.sim_engine` | Abstract timeline generator interface | `__iter__()` |
| `SimulationEvent` | `qstrader.simulation.event` | Event timestamp + category container | `SimulationEvent(ts, event_type)` |
| `DailyBusinessDaySimulationEngine` | `qstrader.simulation.daily_bday` | Daily business day event generator | `DailyBusinessDaySimulationEngine(starting_day, ending_day, ...)` |

---

## Minimal usage examples

### Iterating through simulation events

```python
import pandas as pd
import pytz
from qstrader.simulation.daily_bday import DailyBusinessDaySimulationEngine

start_dt = pd.Timestamp('2024-01-01 00:00:00', tz=pytz.UTC)
end_dt = pd.Timestamp('2024-01-03 23:59:00', tz=pytz.UTC)

sim_engine = DailyBusinessDaySimulationEngine(
    starting_day=start_dt,
    ending_day=end_dt,
    pre_market=True,
    post_market=True
)

for event in sim_engine:
    print(f"{event.ts} -> {event.event_type}")
```

#### Sample Output

```text
2024-01-01 00:00:00+00:00 -> pre_market
2024-01-01 14:30:00+00:00 -> market_open
2024-01-01 21:00:00+00:00 -> market_close
2024-01-01 23:59:00+00:00 -> post_market
2024-01-02 00:00:00+00:00 -> pre_market
...
```

---

## Summary

`qstrader.simulation` provides the event-driven clock for QSTrader backtests. It models time progression via `SimulationEvent` instances yielded by `DailyBusinessDaySimulationEngine`, driving broker updates, exchange operations, and portfolio rebalancing.

