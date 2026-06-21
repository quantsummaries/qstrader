# `qstrader.portcon`

## Overview

The `qstrader.portcon` package (**Portfolio Construction**) is responsible for transforming strategy signals into actionable rebalancing orders. It orchestrates alpha forecasts, risk constraints, portfolio optimization, and order sizing into concrete `Order` objects ready for execution.

The package is organized into three principal layers:

- **Portfolio Construction Engine (`pcm.py`):** `PortfolioConstructionModel` coordinate the entire rebalancing pipeline from signal generation to order creation.
- **Portfolio Optimisers (`qstrader/portcon/optimiser/`):** Abstractions and implementations (`EqualWeightPortfolioOptimiser`, `FixedWeightPortfolioOptimiser`) for allocating portfolio target weights across assets.
- **Order Sizers (`qstrader/portcon/order_sizer/`):** Abstractions and implementations (`DollarWeightedCashBufferedOrderSizer`, `LongShortLeveragedOrderSizer`) for converting dollar target weights into integral asset share quantities, factoring in cash buffers, leverage, and transaction fees.

---

## Package layout

```text
qstrader/portcon/
├── __init__.py
├── pcm.py
├── optimiser/
│   ├── __init__.py
│   ├── equal_weight.py
│   ├── fixed_weight.py
│   └── optimiser.py
└── order_sizer/
    ├── __init__.py
    ├── dollar_weighted.py
    ├── long_short.py
    └── order_sizer.py
```

`qstrader/portcon/__init__.py`, `qstrader/portcon/optimiser/__init__.py`, and `qstrader/portcon/order_sizer/__init__.py` are package markers, so classes are typically imported directly from their respective submodules.

---

## Core abstractions

### `PortfolioConstructionModel`

**Source:** `qstrader/portcon/pcm.py`

`PortfolioConstructionModel` is the top-level callable orchestrator for portfolio construction. When invoked with a timestamp, it executes the multi-stage rebalancing pipeline.

#### Constructor

```python
def __init__(
    self,
    broker: Broker,
    broker_portfolio_id: str,
    universe: Universe,
    order_sizer: OrderSizer,
    optimiser: PortfolioOptimiser,
    alpha_model: AlphaModel | None = None,
    risk_model: RiskModel | None = None,
    cost_model = None,
    data_handler: BacktestDataHandler | None = None,
)
```

- `broker`: The derived `Broker` instance managing portfolios and transaction fee models.
- `broker_portfolio_id`: The specific account/portfolio identifier at the `Broker`.
- `universe`: The `Universe` instance defining available assets for trading.
- `order_sizer`: An `OrderSizer` instance converting target weights to share quantities.
- `optimiser`: A `PortfolioOptimiser` instance refining target asset weights.
- `alpha_model`: Optional `AlphaModel` supplying raw weight signals.
- `risk_model`: Optional `RiskModel` modifying weights based on risk parameters.
- `cost_model`: Optional transaction cost model (reserved for future extension).
- `data_handler`: Optional `BacktestDataHandler` used within portfolio construction routines.

#### Callable signature

```python
def __call__(self, dt: pd.Timestamp, stats: dict | None = None) -> list[Order]
```

#### Rebalancing Pipeline Workflow

When `__call__(dt)` is executed, `PortfolioConstructionModel` follows these steps:

1. **Alpha Signal Generation:** Evaluates `alpha_model(dt)`. If no alpha model is provided, generates a zero-weight vector for all assets in the current `Universe`.
2. **Risk Model Adjustment:** If a `risk_model` is present, passes initial weights through `risk_model(dt, weights)` to adjust for risk constraints.
3. **Portfolio Optimisation:** Passes modified weights through `optimiser(dt, initial_weights=weights)` to obtain `optimised_weights`.
4. **Full Asset List Union:** Obtains the union of all assets in the current `Universe` and any existing positions in the `Broker` portfolio. Assets currently held in the broker portfolio but not present in `optimised_weights` are assigned a weight of `0.0` (signaling liquidation).
5. **Statistics Logging:** If a `stats` dictionary is provided, logs the target allocation vector for timestamp `dt`.
6. **Order Sizing:** Invokes `order_sizer(dt, full_weights)` to translate target percentage weights into integer share quantities (`target_portfolio`).
7. **Current Portfolio Lookup:** Queries `broker.get_portfolio_as_dict(broker_portfolio_id)` to retrieve current position quantities.
8. **Rebalance Order Calculation:** Calculates the delta quantity for each asset (`order_qty = target_qty - current_qty`). Generates `Order` objects for all non-zero delta quantities sorted by asset symbol.
9. **Return:** Returns `list[Order]` ready for submission to execution handlers.

---

## Portfolio Optimisers

### `PortfolioOptimiser`

**Source:** `qstrader/portcon/optimiser/optimiser.py`

`PortfolioOptimiser` is the abstract base class for all target weight optimization strategies.

#### Abstract Interface

```python
class PortfolioOptimiser(object):
    @abstractmethod
    def __call__(self, dt: pd.Timestamp, initial_weights: dict[str, float]) -> dict[str, float]:
        raise NotImplementedError("Should implement __call__()")
```

Subclasses implement `__call__` to convert an initial weight dictionary into an optimized target weight dictionary.

---

### `EqualWeightPortfolioOptimiser`

**Source:** `qstrader/portcon/optimiser/equal_weight.py`

`EqualWeightPortfolioOptimiser` divides total portfolio weight equally among all active assets in `initial_weights`, with an optional scaling factor.

#### Constructor

```python
def __init__(
    self,
    scale: float = 1.0,
    data_handler: BacktestDataHandler | None = None
)
```

- `scale`: Scaling factor applied to equal weights (default `1.0`).
- `data_handler`: Optional data handler preserving interface consistency across optimisers.

#### Sizing Logic

Given $N$ assets in `initial_weights`, each asset is assigned weight $w_i = \text{scale} \times \frac{1.0}{N}$. Initial weight values are ignored; only the dictionary keys (asset symbols) are used.

---

### `FixedWeightPortfolioOptimiser`

**Source:** `qstrader/portcon/optimiser/fixed_weight.py`

`FixedWeightPortfolioOptimiser` is a pass-through optimiser that returns `initial_weights` unmodified.

#### Constructor

```python
def __init__(
    self,
    data_handler: BacktestDataHandler | None = None
)
```

#### Sizing Logic

Returns `initial_weights` directly to downstream components without modification.

---

## Order Sizers

### `OrderSizer`

**Source:** `qstrader/portcon/order_sizer/order_sizer.py`

`OrderSizer` is the abstract base class for converting asset target weights into integer share/unit quantities based on account equity and asset price data.

#### Abstract Interface

```python
class OrderSizer(object):
    @abstractmethod
    def __call__(self, dt: pd.Timestamp, weights: dict[str, float]) -> dict[str, dict]:
        raise NotImplementedError("Should implement call()")
```

Subclasses return a dictionary mapping asset symbols to position specification dictionaries (e.g. `{"ETH": {"quantity": 100}}`).

---

### `DollarWeightedCashBufferedOrderSizer`

**Source:** `qstrader/portcon/order_sizer/dollar_weighted.py`

`DollarWeightedCashBufferedOrderSizer` converts long-only target weights into integer share quantities using current broker portfolio equity, reserving a percentage cash buffer to avoid cash deficit overruns due to non-fractional share rounding and transaction fees.

#### Constructor

```python
def __init__(
    self,
    broker: Broker,
    broker_portfolio_id: str,
    data_handler: BacktestDataHandler,
    cash_buffer_percentage: float = 0.05
)
```

- `broker`: The `Broker` instance used to query account total equity and fee models.
- `broker_portfolio_id`: Specific broker portfolio ID to calculate available equity.
- `data_handler`: `BacktestDataHandler` used to query latest asset ask prices.
- `cash_buffer_percentage`: Cash reserve percentage (between `0.0` and `1.0`, default `0.05` / 5%).

#### Sizing Logic

1. **Cash Buffer Deduction:** Computes usable equity: $E_{\text{buffered}} = E_{\text{total}} \times (1.0 - \text{cash\_buffer\_percentage})$.
2. **Weight Normalisation:** Ensures target weights sum to 1.0 (raises `ValueError` if any negative weight is supplied).
3. **Fee Estimation:** Calculates estimated transaction cost using `broker.fee_model.calc_total_cost`.
4. **Quantity Floor:** Obtains latest ask price $P$ for timestamp `dt`, calculates net dollar allocation $D_{\text{net}} = D_{\text{gross}} - \text{cost}$, and rounds down to nearest integer share count:
   $$\text{quantity} = \lfloor D_{\text{net}} / P \rfloor$$

---

### `LongShortLeveragedOrderSizer`

**Source:** `qstrader/portcon/order_sizer/long_short.py`

`LongShortLeveragedOrderSizer` handles long/short target weights (positive and negative) and scales overall gross exposure according to a target gross leverage multiplier.

#### Constructor

```python
def __init__(
    self,
    broker: Broker,
    broker_portfolio_id: str,
    data_handler: BacktestDataHandler,
    gross_leverage: float = 1.0
)
```

- `broker`: The `Broker` instance used to query account total equity and fee models.
- `broker_portfolio_id`: Specific broker portfolio ID.
- `data_handler`: `BacktestDataHandler` used to query asset prices.
- `gross_leverage`: Gross exposure multiplier (must be $> 0.0$, default `1.0`).

#### Sizing Logic

1. **Leverage Normalisation:** Scales weights so total gross exposure equals `gross_leverage`:
   $$\text{gross\_exposure} = \sum |w_i|, \quad \text{gross\_ratio} = \frac{\text{gross\_leverage}}{\text{gross\_exposure}}, \quad w_i' = w_i \times \text{gross\_ratio}$$
2. **Dollar Allocation & Cost Estimation:** For each asset, computes pre-cost dollar value $D = E_{\text{total}} \times w_i'$, subtracts estimated broker fees, and obtains ask price $P$.
3. **Directional Truncation:** Truncates after-cost dollar weight toward zero ($\lfloor D_{\text{net}} \rfloor$ if $D_{\text{net}} \ge 0$, $\lceil D_{\text{net}} \rceil$ if $D_{\text{net}} < 0$) and divides by price $P$ to yield signed integer share quantities.

---

## System Wiring & Rebalancing Pipeline

```text
               +-----------------------+
               |   Simulation Clock    |
               +-----------+-----------+
                           |
                           v
             PortfolioConstructionModel(dt)
                           |
         +-----------------+-----------------+
         |                 |                 |
         v                 v                 v
   +-----------+     +-----------+     +-----------+
   |AlphaModel |     | RiskModel |     | Universe  |
   +-----+-----+     +-----+-----+     +-----+-----+
         |                 |                 |
         +--------+--------+                 |
                  |                          |
                  v                          v
      +-----------------------+    +-------------------+
      |   PortfolioOptimiser  |    | Broker Portfolio  |
      +-----------+-----------+    +---------+---------|
                  |                          |
                  +------------+-------------+
                               | (full weights union)
                               v
                    +--------------------+
                    |     OrderSizer     |
                    +---------+----------+
                              |
                              v (target portfolio)
                    +--------------------+
                    |  _generate_orders  |
                    +---------+----------+
                              |
                              v
                       list[Order]
```

---

## Quick Reference Table

| Component | Module Path | Inputs / Key Parameters | Primary Outputs / Returns |
| :--- | :--- | :--- | :--- |
| **`PortfolioConstructionModel`** | `qstrader.portcon.pcm` | `broker`, `universe`, `order_sizer`, `optimiser`, `alpha_model`, `risk_model` | `__call__(dt) -> list[Order]` |
| **`PortfolioOptimiser`** | `qstrader.portcon.optimiser.optimiser` | Abstract Interface | `__call__(dt, initial_weights) -> dict[str, float]` |
| **`EqualWeightPortfolioOptimiser`** | `qstrader.portcon.optimiser.equal_weight` | `scale=1.0`, `data_handler=None` | Equal weight vector scaled by `scale` |
| **`FixedWeightPortfolioOptimiser`** | `qstrader.portcon.optimiser.fixed_weight` | `data_handler=None` | `initial_weights` unchanged |
| **`OrderSizer`** | `qstrader.portcon.order_sizer.order_sizer` | Abstract Interface | `__call__(dt, weights) -> dict[str, dict]` |
| **`DollarWeightedCashBufferedOrderSizer`** | `qstrader.portcon.order_sizer.dollar_weighted` | `broker`, `portfolio_id`, `data_handler`, `cash_buffer_percentage=0.05` | Long-only share quantities dictionary |
| **`LongShortLeveragedOrderSizer`** | `qstrader.portcon.order_sizer.long_short` | `broker`, `portfolio_id`, `data_handler`, `gross_leverage=1.0` | Signed long/short share quantities dictionary |

---

## Minimal Usage Example

```python
import pandas as pd
from qstrader.portcon.pcm import PortfolioConstructionModel
from qstrader.portcon.optimiser.equal_weight import EqualWeightPortfolioOptimiser
from qstrader.portcon.order_sizer.dollar_weighted import DollarWeightedCashBufferedOrderSizer

# Initialize optimiser and order sizer
optimiser = EqualWeightPortfolioOptimiser(scale=1.0)
order_sizer = DollarWeightedCashBufferedOrderSizer(
    broker=broker,
    broker_portfolio_id="default",
    data_handler=data_handler,
    cash_buffer_percentage=0.05
)

# Construct PCM orchestrator
pcm = PortfolioConstructionModel(
    broker=broker,
    broker_portfolio_id="default",
    universe=universe,
    order_sizer=order_sizer,
    optimiser=optimiser,
    alpha_model=alpha_model,
    risk_model=risk_model
)

# Execute rebalance at timestamp
dt = pd.Timestamp("2020-01-02 14:30:00", tz="UTC")
rebalance_orders = pcm(dt)

# Output orders to execution handler
for order in rebalance_orders:
    print(f"Order: {order.action} {order.quantity} units of {order.asset}")
```

