# `qstrader.signals`

## Overview

The `qstrader.signals` package provides the **indicator and signal generation layer** for QSTrader. It manages rolling historical price data buffers and calculates technical indicators (such as simple moving averages, momentum, and annualized volatility) used by alpha models and risk models.

The package is built around four primary components:

- **Price Buffer Management** — `AssetPriceBuffers` stores fixed-length double-ended queues (`collections.deque`) for individual asset lookback periods.
- **Abstract Base Interface** — `Signal` defines the interface and lifecycle for lookback-based indicator calculations across a universe of assets.
- **Concrete Indicator Calculations** — `SMASignal`, `MomentumSignal`, and `VolatilitySignal` compute specific quantitative time-series metrics.
- **Signal Aggregation & Data Updating** — `SignalsCollection` aggregates multiple `Signal` instances and coordinates daily market price updates during simulation runs.

---

## Package layout

```text
qstrader/signals/
├── __init__.py
├── buffer.py
├── momentum.py
├── signal.py
├── signals_collection.py
├── sma.py
└── vol.py
```

`qstrader/signals/__init__.py` is currently empty, so imports are made directly from concrete modules.

---

## Core Architecture & Key Concepts

```text
SignalsCollection
 ├── data_handler               BacktestDataHandler
 ├── warmup                     int (counts simulation updates)
 └── signals                    dict[str → Signal]
      └── Signal (e.g. MomentumSignal, SMASignal, VolatilitySignal)
           ├── start_dt         pd.Timestamp
           ├── universe         Universe (StaticUniverse or DynamicUniverse)
           ├── lookbacks        list[int]
           └── buffers          AssetPriceBuffers
                 └── prices     dict[key → deque[float]]  (key format: "{asset}_{lookback}")
```

### 1. Rolling Lookback Price Buffers
Indicators in `qstrader.signals` rely on price history stored in Python `collections.deque` objects with maximum length `maxlen=lookback`. When a new daily mid-price is appended, older prices are automatically evicted once the buffer capacity is reached.

### 2. The "Bumped Lookback" Pattern
To calculate $N$-period percentage returns (such as for momentum or volatility), $N+1$ price points are required. Concrete return-based indicators (`MomentumSignal` and `VolatilitySignal`) automatically increment requested lookbacks by 1 (`bumped_lookbacks = [lookback + 1 for lookback in lookbacks]`) when initializing their base price buffers, keeping internal buffer lookback details transparent to callers.

### 3. Dynamic Universe Support
When assets enter a `DynamicUniverse` after the start of a simulation, signals dynamically discover and initialize new price buffers for those assets via `update_assets(dt)` and auto-instantiation in `AssetPriceBuffers.append(...)`.

### 4. Simulation Integration
During a backtest, `BacktestTradingSession` invokes `SignalsCollection.update(dt)` on every `market_close` event. This fetches the latest mid-prices from the data handler, updates all asset buffers, and increments the `warmup` period counter.

---

## Core Interface & Infrastructure Classes

### `Signal`

**Source:** `qstrader/signals/signal.py`

`Signal(ABC)` is the abstract base class for all rolling price-buffer signal implementations. It manages initial universe discovery, instantiates `AssetPriceBuffers`, and handles dynamic asset additions over time.

#### Constructor

```python
Signal(start_dt: pd.Timestamp, universe: Universe, lookbacks: list[int])
```

#### Parameters

- `start_dt: pd.Timestamp` — start datetime (UTC) of the signal.
- `universe: Universe` — the universe of assets (e.g. `StaticUniverse` or `DynamicUniverse`) for which signals are calculated.
- `lookbacks: list[int]` — list of lookback periods (e.g. `[50, 200]`) to store price buffers for.

#### Attributes

- `start_dt: pd.Timestamp`
- `universe: Universe`
- `lookbacks: list[int]`
- `assets: list[str]` — active asset symbols at `start_dt` obtained from `universe.get_assets(start_dt)`.
- `buffers: AssetPriceBuffers` — price buffer storage created via `_create_asset_price_buffers()`.

#### Key Methods

```python
_create_asset_price_buffers() -> AssetPriceBuffers
```

Protected helper method called during `__init__` that instantiates `AssetPriceBuffers(self.assets, lookbacks=self.lookbacks)`.

```python
append(asset: str, price: float) -> None
```

Appends a new price point into `self.buffers` for the specified asset. Delegates directly to `self.buffers.append(asset, price)`.

```python
update_assets(dt: pd.Timestamp) -> None
```

Queries `universe.get_assets(dt)` and appends any newly introduced asset symbols to `self.assets`. Actual price buffer creation for these new assets is handled lazily when `append(asset, price)` is invoked for the asset.

```python
@abstractmethod
__call__(asset: str, lookback: int)
```

Abstract method that calculates and returns the scalar signal value (e.g., SMA value, momentum return, or annualized volatility) for a given asset and lookback period. Must be implemented by concrete subclasses.

---

### `AssetPriceBuffers`

**Source:** `qstrader/signals/buffer.py`

Utility class that maintains double-ended queues (`collections.deque`) of historical asset prices for specified lookback timeframes.

#### Constructor

```python
AssetPriceBuffers(assets: list[str], lookbacks: list[int] = [12])
```

#### Parameters

- `assets: list[str]` — list of active asset symbol strings.
- `lookbacks: list[int]` — list of lookback periods (e.g. `[50, 200]` for fast/slow SMAs or `[21, 63, 252]` for multi-period momentum).

#### Design Rationale: `lookbacks: list[int]`
Taking a list of integer lookback periods rather than a single integer allows a single `AssetPriceBuffers` instance to:
1. **Support Multi-Horizon Indicators**: Maintain buffers for multiple timeframe windows simultaneously (e.g., dual moving average crossovers or multi-period momentum rankings).
2. **Single-Pass Appends**: Fan-out daily price updates across all configured lookback deques for an asset in a single `append()` call.
3. **Memory Efficiency**: Size each queue independently with `deque(maxlen=lookback)` so older prices beyond each window are automatically evicted without manual array slicing.

#### Key Lookup Format

Buffer deques are stored in `self.prices: dict[str, deque[float]]` using lookup keys formatted by `_asset_lookback_key(asset, lookback)` as `f"{asset}_{lookback}"` (e.g., `'EQ:SPY_12'`).

#### Public Methods

```python
add_asset(asset: str) -> None
```

Explicitly initializes price buffers for a newly added asset symbol. Raises `ValueError` if the asset already exists in `self.assets`.

```python
append(asset: str, price: float) -> None
```

Appends a new price into all lookback deques for `asset`.

- **Validation:** Raises `ValueError` if `price <= 0.0`.
- **Dynamic Asset Discovery:** Checks key existence (`_asset_lookback_key(asset, self.lookbacks[0]) in self.prices`); if absent (such as when an asset enters a `DynamicUniverse` mid-backtest), automatically creates its price buffer dictionary on the fly before appending.

---

### `SignalsCollection`

**Source:** `qstrader/signals/signals_collection.py`

Aggregates multiple `Signal` instances and coordinates updating their price buffers from market data handlers during backtest simulation loops.

#### Constructor

```python
SignalsCollection(signals: dict[str, Signal], data_handler: BacktestDataHandler)
```

#### Parameters

- `signals: dict[str, Signal]` — dictionary mapping custom signal names to `Signal` instances.
- `data_handler: BacktestDataHandler` — data handler used to query mid-prices.

#### Attributes

- `signals: dict[str, Signal]`
- `data_handler: BacktestDataHandler`
- `warmup: int` — tracks the number of simulation market-close updates processed.

#### Public Methods

```python
__getitem__(signal: str) -> Signal
```

Enables dictionary-like syntax to retrieve signals (e.g., `signals['momentum']`).

```python
update(dt: pd.Timestamp) -> None
```

Updates universe membership for all managed signals, retrieves the latest mid-price for each asset via `data_handler.get_asset_latest_mid_price(dt, asset)`, appends the prices into the respective signal buffers, and increments `self.warmup` by 1.

---

## Concrete Indicator Implementations

### `SMASignal`

**Source:** `qstrader/signals/sma.py`

Calculates the Simple Moving Average (SMA) of asset prices over the last $N$ periods.

#### Formula

$$\text{SMA}(N) = \frac{1}{N} \sum_{i=1}^{N} P_i$$

#### Constructor

```python
SMASignal(start_dt: pd.Timestamp, universe: Universe, lookbacks: list[int])
```

#### Calculation Behavior

```python
def __call__(self, asset: str, lookback: int) -> float:
    return np.mean(self.buffers.prices['%s_%s' % (asset, lookback)])
```

Computes the arithmetic mean of all price values currently in the lookback deque for `asset`.

---

### `MomentumSignal`

**Source:** `qstrader/signals/momentum.py`

Calculates holding-period return momentum (cumulative return) over the last $N$ periods.

#### Formula

$$R_{\text{cum}} = \prod_{t=1}^{N} (1 + r_t) - 1 = \frac{P_N}{P_0} - 1$$

#### Constructor

```python
MomentumSignal(start_dt: pd.Timestamp, universe: Universe, lookbacks: list[int])
```

#### Internal Lookback Bumping

In `__init__`, requested lookbacks are bumped by 1 (`[lookback + 1 for lookback in lookbacks]`) to store $N+1$ prices so that $N$ period percentage returns can be computed. Lookup keys use `f"{asset}_{lookback + 1}"`.

#### Calculation Behavior

1. Retrieves price buffer series for `f"{asset}_{lookback + 1}"`.
2. Computes percentage returns via `Series.pct_change().dropna().to_numpy()`.
3. If fewer than 1 return point is available, returns `0.0`.
4. Otherwise returns `(np.cumprod(1.0 + returns) - 1.0)[-1]`.

---

### `VolatilitySignal`

**Source:** `qstrader/signals/vol.py`

Calculates annualized daily return volatility over the last $N$ periods.

#### Formula

$$\sigma_{\text{ann}} = \text{std}(r_t) \times \sqrt{252}$$

#### Constructor

```python
VolatilitySignal(start_dt: pd.Timestamp, universe: Universe, lookbacks: list[int])
```

#### Internal Lookback Bumping

Like `MomentumSignal`, `VolatilitySignal` bumps requested lookbacks by 1 to store $N+1$ prices, providing $N$ return observations. Lookup keys use `f"{asset}_{lookback + 1}"`.

#### Calculation Behavior

1. Retrieves price buffer series for `f"{asset}_{lookback + 1}"`.
2. Computes percentage returns via `Series.pct_change().dropna().to_numpy()`.
3. If fewer than 1 return point is available, returns `0.0`.
4. Otherwise returns `np.std(returns) * np.sqrt(252)`.

---

## Integration with QSTrader Framework

### 1. Backtest Trading Session Loop
`BacktestTradingSession` manages signal updates automatically when `signals` is supplied:

```python
# Inside BacktestTradingSession.run() event loop:
if self.signals is not None and event.event_type == "market_close":
    self.signals.update(dt)
```

### 2. Alpha Model Consumption
Custom alpha models receive `signals: SignalsCollection` in their constructor and check `signals.warmup` against necessary lookbacks before generating signals:

```python
class TopNMomentumAlphaModel(AlphaModel):
    def __init__(self, signals, mom_lookback, ...):
        self.signals = signals
        self.mom_lookback = mom_lookback

    def __call__(self, dt):
        assets = self.universe.get_assets(dt)
        weights = {asset: 0.0 for asset in assets}

        # Check warmup period before calculating momentum signals
        if self.signals.warmup >= self.mom_lookback:
            momenta = {
                asset: self.signals['momentum'](asset, self.mom_lookback)
                for asset in assets
            }
            # ... select top momentum assets and calculate target weights ...

        return weights
```

---

## Observed Test Coverage

Unit tests in `tests/unit/signals/` validate signal behavior:

- `test_sma.py`
  - Mocks `Universe.get_assets` returning `['EQ:SPY']`.
  - Appends 15 price points to `SMASignal` with lookbacks `[6, 12]`.
  - Asserts calculated moving averages match expected numpy mean values using `np.isclose`.
- `test_momentum.py`
  - Mocks `Universe.get_assets` returning `['EQ:SPY']`.
  - Appends 15 price points to `MomentumSignal` with lookbacks `[6, 12]`.
  - Asserts calculated holding-period returns match expected cumulative returns using `np.isclose`.

---

## Example Usage in Repository

`examples/momentum_taa.py` demonstrates using `MomentumSignal` and `SignalsCollection` in a Tactical Asset Allocation (TAA) strategy across US Sector ETFs (`XLB`, `XLE`, `XLF`, etc.):

```python
# 1. Instantiate the signal
momentum = MomentumSignal(start_dt, strategy_universe, lookbacks=[mom_lookback])

# 2. Wrap signal in SignalsCollection
signals = SignalsCollection({'momentum': momentum}, strategy_data_handler)

# 3. Create custom AlphaModel consuming SignalsCollection
strategy_alpha_model = TopNMomentumAlphaModel(
    signals, mom_lookback, mom_top_n, strategy_universe, strategy_data_handler
)

# 4. Pass signals collection into BacktestTradingSession
strategy_backtest = BacktestTradingSession(
    start_dt, end_dt, strategy_universe, strategy_alpha_model,
    signals=signals,
    rebalance='end_of_month',
    ...
)
```

---

## Design Notes & Limitations

- **Price Positivity Check:** `AssetPriceBuffers.append` raises `ValueError` for prices $\le 0.0$.
- **Lookback Length Off-By-One:** `MomentumSignal` and `VolatilitySignal` require $N+1$ prices to calculate $N$ return values. Handled automatically via internal lookback bumping.
- **Dynamic Universe Memory:** When assets enter a dynamic universe, buffers are created automatically. If an asset leaves the universe, its buffer remains stored in memory.
- **Data Dependency:** `SignalsCollection.update(dt)` fetches asset mid-prices (`get_asset_latest_mid_price`). It assumes all active assets in the universe have valid mid-price entries at every simulation tick.
- **Module Imports:** `qstrader/signals/__init__.py` is empty, so classes must be imported from their respective module files (`qstrader.signals.momentum`, `qstrader.signals.sma`, `qstrader.signals.vol`, `qstrader.signals.signals_collection`, etc.).

---

## Quick Reference

| Class | Module | Purpose | Key API |
|---|---|---|---|
| `Signal` | `qstrader.signals.signal` | Abstract base class for rolling indicators | `__call__(asset: str, lookback: int)` |
| `AssetPriceBuffers` | `qstrader.signals.buffer` | `deque`-based price storage per asset & lookback | `append(asset: str, price: float)` |
| `SignalsCollection` | `qstrader.signals.signals_collection` | Aggregates signals & updates from data handler | `update(dt: pd.Timestamp)` |
| `SMASignal` | `qstrader.signals.sma` | Simple Moving Average | `SMASignal(start_dt, universe, lookbacks)` |
| `MomentumSignal` | `qstrader.signals.momentum` | Cumulative return (holding period return) | `MomentumSignal(start_dt, universe, lookbacks)` |
| `VolatilitySignal` | `qstrader.signals.vol` | Annualized return volatility ($\sigma \times \sqrt{252}$) | `VolatilitySignal(start_dt, universe, lookbacks)` |

---

## Minimal Usage Examples

### 1. Manual Price Buffer Operations

```python
import pandas as pd
import pytz
from qstrader.asset.universe.static import StaticUniverse
from qstrader.signals.sma import SMASignal

start_dt = pd.Timestamp('2020-01-01 14:30:00', tz=pytz.UTC)
universe = StaticUniverse(['EQ:SPY'])
sma = SMASignal(start_dt, universe, lookbacks=[5, 10])

# Append 5 prices for EQ:SPY
for price in [100.0, 102.0, 101.0, 103.0, 104.0]:
    sma.append('EQ:SPY', price)

# Query SMA for 5-period lookback
print(sma('EQ:SPY', 5))  # 102.0
```

### 2. Using `SignalsCollection` with a Data Handler

```python
from qstrader.signals.momentum import MomentumSignal
from qstrader.signals.vol import VolatilitySignal
from qstrader.signals.signals_collection import SignalsCollection

mom = MomentumSignal(start_dt, universe, lookbacks=[20])
vol = VolatilitySignal(start_dt, universe, lookbacks=[20])

signals = SignalsCollection(
    {'momentum': mom, 'volatility': vol},
    data_handler=data_handler
)

# On simulation tick
signals.update(current_dt)

# Access signals
current_mom = signals['momentum']('EQ:SPY', 20)
current_vol = signals['volatility']('EQ:SPY', 20)
```

---

## Summary

`qstrader.signals` provides a modular time-series buffer and technical indicator pipeline. By separating price deque buffering (`AssetPriceBuffers`), indicator formulas (`SMASignal`, `MomentumSignal`, `VolatilitySignal`), and backtest loop synchronization (`SignalsCollection`), strategy developers can easily consume pre-computed signals or extend `Signal` to create custom technical indicators.

