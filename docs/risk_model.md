# `qstrader.risk_model`

## Overview

The `qstrader.risk_model` package defines the **risk-adjustment hook** in the QSTrader portfolio construction pipeline.

At each rebalance timestamp, a risk model can take the raw alpha weights/signals and return adjusted weights before portfolio optimisation and order sizing.

The package currently contains a single abstract interface:

- **Risk model interface (`risk_model.py`)**: `RiskModel` abstract base class defining `__call__(dt, weights)`.

---

## Package layout

```text
qstrader/risk_model/
├── __init__.py
└── risk_model.py
```

`qstrader/risk_model/__init__.py` is empty.

---

## Core abstraction

### `RiskModel`

**Source:** `qstrader/risk_model/risk_model.py`

`RiskModel` is an abstract callable interface for modifying portfolio weights/signals generated upstream by an alpha model.

```python
from abc import ABC, abstractmethod
import pandas as pd


class RiskModel(ABC):
    @abstractmethod
    def __call__(self, dt: pd.Timestamp, weights: list[float]):
        raise NotImplementedError("Should implement __call__()")
```

#### Method contract

- `dt: pd.Timestamp` - current rebalance timestamp.
- `weights` - alpha-produced candidate weights/signals to adjust.
- Return value - adjusted weights/signals consumed by the optimiser.

#### Important note on types

The annotation in `risk_model.py` is `weights: list[float]`, but the surrounding portfolio-construction flow is dictionary-based (`dict[str, float]`) in practice. A custom risk model should follow the actual runtime contract used by `PortfolioConstructionModel` and return a structure compatible with the optimiser (typically a symbol-keyed dictionary).

---

## Where it is used in QSTrader

### 1. Backtest session wiring

`BacktestTradingSession` accepts an optional risk model and passes it into `QuantTradingSystem`:

- `qstrader/trading/backtest.py` (`risk_model` constructor argument)
- `qstrader/trading/backtest.py` (`_create_quant_trading_system`)

### 2. System model assembly

`QuantTradingSystem` stores `risk_model` and injects it into `PortfolioConstructionModel`:

- `qstrader/system/qts.py` (`risk_model` constructor argument)
- `qstrader/system/qts.py` (`_initialise_models`)

### 3. Portfolio construction execution

`PortfolioConstructionModel.__call__` applies the risk model immediately after alpha generation and before optimisation:

```python
if self.alpha_model:
    weights = self.alpha_model(dt)
else:
    weights = self._create_zero_target_weights_vector(dt)

if self.risk_model:
    weights = self.risk_model(dt, weights)

optimised_weights = self.optimiser(dt, initial_weights=weights)
```

**Source:** `qstrader/portcon/pcm.py`

---

## Execution order in the rebalance pipeline

At each rebalance timestamp the relevant processing order is:

1. `AlphaModel` generates candidate weights/signals.
2. `RiskModel` optionally adjusts or constrains those values.
3. `PortfolioOptimiser` converts adjusted values to target weights.
4. `OrderSizer` transforms target weights into integer quantities.
5. `ExecutionHandler` submits/simulates orders.

---

## Minimal custom implementation example

```python
import pandas as pd
from qstrader.risk_model.risk_model import RiskModel


class MaxAbsWeightRiskModel(RiskModel):
    """
    Clip each symbol's absolute weight to a fixed bound.
    """

    def __init__(self, max_abs_weight: float = 0.25):
        self.max_abs_weight = float(max_abs_weight)

    def __call__(self, dt: pd.Timestamp, weights: dict[str, float]) -> dict[str, float]:
        clipped = {
            asset: max(-self.max_abs_weight, min(self.max_abs_weight, w))
            for asset, w in weights.items()
        }
        return clipped
```

You can pass this instance into `BacktestTradingSession(..., risk_model=...)`.

---

## Current limitations

- No concrete `RiskModel` implementations are included in the repository.
- No dedicated `tests/unit/risk_model/` coverage currently exists.
- The base interface type annotation (`list[float]`) does not reflect the common symbol-keyed dictionary usage in the pipeline.

---

## Summary

`qstrader.risk_model` is intentionally minimal: a single abstract callback interface used to inject risk controls between alpha generation and portfolio optimisation. It is the primary extension point for constraints and exposure-shaping logic in QSTrader backtests.

