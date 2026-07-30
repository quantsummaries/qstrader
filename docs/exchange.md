# `qstrader.exchange`

## Overview

The `qstrader.exchange` package models trading venue calendar logic for QSTrader backtesting simulations. It determines whether a trading venue (such as the NYSE or LSE) is open at a given timestamp so that the broker knows when orders can be executed.

In the current codebase, the package is intentionally lightweight:

- `Exchange` defines the abstract base interface.
- `SimulatedExchange` models a simplified venue with fixed weekday trading hours.

---

## Package layout

```text
qstrader/exchange/
├── __init__.py
├── exchange.py
└── simulated_exchange.py
```

`qstrader/exchange/__init__.py` is currently empty, so imports are typically made directly from the concrete module paths.

---

## Core interface

### `Exchange`

**Source:** `qstrader/exchange/exchange.py`

`Exchange` is the abstract base class for all exchange implementations.

```python
class Exchange(object):
    @abstractmethod
    def is_open_at_datetime(self, dt: pd.Timestamp) -> bool:
        ...
```

#### Contract

Implementations must provide:

```text
is_open_at_datetime(dt: pd.Timestamp) -> bool
```

where `dt` is a `pd.Timestamp` representing the time to evaluate. It returns `True` if the trading venue is open for order execution at that timestamp, and `False` otherwise.

#### Design intent

This abstraction decouples execution mechanics from specific exchange calendars, allowing future implementations (e.g. holiday-aware calendars, multiple timezones, or live exchange connectors) without altering broker or trading session logic.

---

## Implementations

### `SimulatedExchange`

**Source:** `qstrader/exchange/simulated_exchange.py`

`SimulatedExchange` models a simulated trading venue for backtesting workflows.

#### Constructor

```python
SimulatedExchange(start_dt: pd.Timestamp)
```

#### Parameters

- `start_dt: pd.Timestamp` — the simulation start datetime.

#### Stored attributes

- `start_dt: pd.Timestamp` — stored start timestamp.
- `open_dt: datetime.time` — set to `14:30` (default NYSE market open in UTC).
- `close_dt: datetime.time` — set to `21:00` (default NYSE market close in UTC).

#### Method behavior

```python
def is_open_at_datetime(self, dt: pd.Timestamp) -> bool:
    if dt.weekday() > 4:
        return False
    return self.open_dt <= dt.time() and dt.time() < self.close_dt
```

- **Weekday check:** returns `False` if `dt.weekday() > 4` (Saturdays and Sundays).
- **Hours check:** returns `True` if `14:30 <= dt.time() < 21:00`.
- **Calendar & Holidays:** does not query historical exchange holiday schedules.

---

## How exchange is used in QSTrader

### 1. Backtest session initialization

`BacktestTradingSession` in `qstrader/trading/backtest.py` creates a default `SimulatedExchange` during setup:

```python
def _create_exchange(self):
    return SimulatedExchange(self.start_dt)
```

This exchange instance is then passed directly into `SimulatedBroker`.

### 2. Order execution in broker

`SimulatedBroker` in `qstrader/broker/simulated_broker.py` queries the exchange inside its tick update loop (`update(dt)`):

```python
if self.exchange.is_open_at_datetime(dt):
    # Drain open order queues and execute orders
```

If the exchange is closed at timestamp `dt`, open orders remain queued until the venue opens.

---

## Observed test coverage and integration

While unit tests focus primarily on downstream components (`SimulatedBroker`, `BacktestTradingSession`), integration tests in `tests/integration/portcon/test_pcm_e2e.py` and `tests/integration/trading/test_backtest_e2e.py` instantiate `SimulatedExchange` to verify end-to-end backtest execution.

---

## Design notes and limitations

- **Fixed market hours:** `open_dt` (14:30) and `close_dt` (21:00) are hardcoded to standard US equity market hours (expressed in UTC).
- **No holiday calendar:** statutory market holidays (e.g. Thanksgiving, Christmas, Independence Day) are not modeled.
- **Single venue:** currently assumes a single global venue per simulation; multi-exchange or cross-border trading schedules require subclassing `Exchange`.
- **`__init__.py` re-exports:** `qstrader/exchange/__init__.py` is currently empty; modules must be imported directly.

---

## Quick reference

| Class | Module | Purpose | Key API |
|---|---|---|---|
| `Exchange` | `qstrader.exchange.exchange` | Abstract exchange calendar interface | `is_open_at_datetime(dt: pd.Timestamp) -> bool` |
| `SimulatedExchange` | `qstrader.exchange.simulated_exchange` | Simulated venue with fixed market hours | `SimulatedExchange(start_dt: pd.Timestamp)` |

---

## Minimal usage examples

### Instantiating and querying `SimulatedExchange`

```python
import pandas as pd
import pytz
from qstrader.exchange.simulated_exchange import SimulatedExchange

start_dt = pd.Timestamp('2024-01-01 00:00:00', tz=pytz.UTC)
exchange = SimulatedExchange(start_dt)

# Wednesday at market open (14:30 UTC)
open_time = pd.Timestamp('2024-01-03 14:30:00', tz=pytz.UTC)
print(exchange.is_open_at_datetime(open_time))  # True

# Saturday (Weekend)
weekend_time = pd.Timestamp('2024-01-06 15:00:00', tz=pytz.UTC)
print(exchange.is_open_at_datetime(weekend_time))  # False
```

---

## Summary

`qstrader.exchange` provides the trading-venue calendar abstraction for QSTrader. It allows `SimulatedBroker` and `BacktestTradingSession` to evaluate whether market venues are open before executing orders during a backtest.

