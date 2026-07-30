# `qstrader.alpha_model`

## Overview

The `qstrader.alpha_model` package defines the **signal-generation layer** for QSTrader.

An alpha model is a callable object that receives a timestamp and returns a dictionary of scalar forecast values keyed by asset symbol (for example `EQ:SPY`). These forecasts are consumed by portfolio construction to create target portfolio weights.

In the current codebase, this package is intentionally lightweight:

- `AlphaModel` defines the abstract interface.
- `FixedSignalsAlphaModel` returns a pre-specified signal map.
- `SingleSignalAlphaModel` returns one shared signal value for every asset currently in the universe.

---

## Package layout

```text
qstrader/alpha_model/
├── __init__.py
├── alpha_model.py
├── fixed_signals.py
└── single_signal.py
```

`qstrader/alpha_model/__init__.py` is currently empty, so imports are typically made from concrete modules.

---

## Core interface

### `AlphaModel`

**Source:** `qstrader/alpha_model/alpha_model.py`

`AlphaModel` is the abstract interface for all alpha-model implementations.

```python
class AlphaModel(object):
    @abstractmethod
    def __call__(self, dt: pd.Timestamp) -> dict[str, float]:
        ...
```

#### Contract

Implementations must provide:

```text
__call__(dt: pd.Timestamp) -> dict[str, float]
```

where:

- keys are asset symbols (for example `EQ:AGG`),
- values are scalar forecast/signal values.

#### Design intent

The class docstring states that alpha models can optionally depend on a universe and data handler. This keeps the interface flexible for both simple static models and richer data-driven models.

---

## Implementations

### `FixedSignalsAlphaModel`

**Source:** `qstrader/alpha_model/fixed_signals.py`

Returns a fixed dictionary of signal weights every time it is called.

#### Constructor

```python
FixedSignalsAlphaModel(signal_weights: dict[str, float], universe: Universe|None=None, data_handler=None)
```

#### Parameters

- `signal_weights: dict[str, float]` - signal value per asset symbol.
- `universe: Universe | None` - optional; stored for interface consistency.
- `data_handler: DataHandler | None` - optional; stored for interface consistency.

#### Behavior

```python
def __call__(self, dt: pd.Timestamp):
    return self.signal_weights
```

- `dt` is accepted for interface compatibility.
- The return value does not depend on time.
- `universe` is not queried by this implementation.

#### Typical use

Use this model when target exposures are static and known in advance (for example buy-and-hold or a fixed 60/40-style allocation).

---

### `SingleSignalAlphaModel`

**Source:** `qstrader/alpha_model/single_signal.py`

Creates a dictionary that applies the same scalar signal to every asset currently available in the universe.

#### Constructor

```python
SingleSignalAlphaModel(universe: Universe, signal: float=1.0, data_handler=None)
```

#### Parameters

- `universe: Universe` - required; queried to obtain the active assets at `dt`.
- `signal: float` - scalar value applied to every returned asset key.
- `data_handler: DataHandler | None` - optional; stored for interface consistency.

#### Behavior

```python
def __call__(self, dt: pd.Timestamp) -> dict[str, float]:
    assets = self.universe.get_assets(dt)
    return {asset: self.signal for asset in assets}
```

- Output can vary over time if the universe composition changes.
- With a `StaticUniverse`, output keys are stable through time.
- With a dynamic universe, assets can appear in the signal map as they enter the universe.

#### Typical use

Use this model when you want equal directional conviction across all current universe members (for example all long at `+1.0`, or all short at `-0.25`).

---

## How alpha models are used in QSTrader

### Portfolio construction

`qstrader/portcon/pcm.py` consumes the alpha model in `PortfolioConstructionModel.__call__`:

```python
if self.alpha_model:
    weights = self.alpha_model(dt)
else:
    weights = self._create_zero_target_weights_vector(dt)
```

So the alpha model output is the initial target-weight suggestion before optional risk-model overrides and optimization.

### Backtest session wiring

`qstrader/trading/backtest.py` requires an `alpha_model` argument in `BacktestTradingSession(...)`.

This means every standard backtest strategy in this repository has an explicit alpha-model component, even if very simple.

---

## Observed test coverage

Unit tests in `tests/unit/alpha_model/` validate both concrete models:

- `test_fixed_signals.py`
  - parameterizes multiple signal dictionaries,
  - verifies `FixedSignalsAlphaModel(dt)` returns the same dictionary unchanged.
- `test_single_signal.py`
  - parameterizes both positive and negative scalar values,
  - mocks `universe.get_assets(...)`,
  - verifies all returned assets receive the configured scalar signal.

This test coverage confirms the current package behavior as deterministic and minimal.

---

## Example usage in repository

### Fixed, single-asset buy and hold

`examples/buy_and_hold.py`:

```python
strategy_alpha_model = FixedSignalsAlphaModel({'EQ:GLD': 1.0})
```

This creates a persistent 100% signal on `EQ:GLD`.

### Additional fixed-allocation examples

Other examples such as `examples/sixty_forty.py`, `examples/sixty_forty_fees.py`, and `examples/long_short.py` follow the same pattern with multi-asset fixed signal maps.

---

## Design notes and limitations

- The package currently ships only **constant-signal** models.
- Both implementations store `data_handler`, but neither currently uses it.
- `FixedSignalsAlphaModel` does not validate that `signal_weights` keys match the universe.
- `SingleSignalAlphaModel` depends on `universe.get_assets(dt)` and assumes it returns symbol strings.
- `qstrader/alpha_model/__init__.py` does not re-export public classes.

---

## Quick reference

| Class | Module | Purpose | Key API |
|---|---|---|---|
| `AlphaModel` | `qstrader.alpha_model.alpha_model` | Abstract alpha-model interface | `__call__(dt: pd.Timestamp) -> dict[str, float]` |
| `FixedSignalsAlphaModel` | `qstrader.alpha_model.fixed_signals` | Return fixed symbol->signal mapping | `FixedSignalsAlphaModel(signal_weights: dict[str, float], universe: Universe|None=None, data_handler=None)` |
| `SingleSignalAlphaModel` | `qstrader.alpha_model.single_signal` | Apply one scalar signal to all current universe assets | `SingleSignalAlphaModel(universe: Universe, signal: float=1.0, data_handler=None)` |

---

## Minimal usage examples

### Fixed mapping

```python
from qstrader.alpha_model.fixed_signals import FixedSignalsAlphaModel

alpha = FixedSignalsAlphaModel({
    'EQ:SPY': 0.6,
    'EQ:AGG': 0.4,
})
signals = alpha(dt)
```

### Uniform signal over the current universe

```python
from qstrader.alpha_model.single_signal import SingleSignalAlphaModel
from qstrader.asset.universe.static import StaticUniverse

universe = StaticUniverse(['EQ:SPY', 'EQ:AGG', 'EQ:GLD'])
alpha = SingleSignalAlphaModel(universe=universe, signal=1.0)
signals = alpha(dt)
# {'EQ:SPY': 1.0, 'EQ:AGG': 1.0, 'EQ:GLD': 1.0}
```

---

## Summary

`qstrader.alpha_model` is the strategy forecast interface used by QSTrader portfolio construction. In the current repository it provides a compact abstraction with two concrete, deterministic implementations suitable for static or uniform-allocation workflows, and serves as the extension point for richer, data-driven alpha generation.

