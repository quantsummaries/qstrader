# `qstrader.asset`

## Overview

The `qstrader.asset` package defines the basic asset abstractions used throughout QSTrader, along with simple universe objects that control which asset symbols are tradable at a given time.

In the current codebase, the package is intentionally lightweight:

- `Asset` is a minimal abstract base for asset metadata.
- `Cash` models a cash-like holding.
- `Equity` models a stock or ETF.
- `Universe` and its subclasses provide time-aware lists of asset symbols.

A practical detail in this repository is that many subsystems operate on **asset symbol strings** such as `EQ:SPY`, even when asset classes like `Equity` also exist as Python objects.

---

## Package layout

```text
qstrader/asset/
├── __init__.py
├── asset.py
├── cash.py
├── equity.py
└── universe/
    ├── __init__.py
    ├── dynamic.py
    ├── static.py
    └── universe.py
```

Both `__init__.py` files are currently empty, so imports are typically made from the concrete module paths.

---

## Core classes

### `Asset`

**Source:** `qstrader/asset/asset.py`

`Asset` is the root base class for trading assets.

```python
class Asset(object):
    __metaclass__ = ABCMeta
```

#### Purpose

- Acts as a shared parent type for concrete asset classes.
- Establishes the intent that asset implementations belong to a common hierarchy.

#### Notes

- The class does not currently define any abstract methods or shared attributes.
- In practice, concrete subclasses such as `Cash` and `Equity` define their own fields.

---

### `Cash`

**Source:** `qstrader/asset/cash.py`

`Cash` stores metadata for a cash-like asset.

#### Constructor

```python
Cash(currency='USD')
```

#### Attributes

- `cash_like: bool` — always set to `True`
- `currency: str` — the currency code, defaulting to `"USD"`

#### Behavior

`Cash` is a very small metadata container. It does not currently implement pricing, FX conversion, or accounting logic by itself.

#### Example

```python
from qstrader.asset.cash import Cash

base_cash = Cash()
gbp_cash = Cash('GBP')
```

#### Observed test coverage

Unit tests verify that:

- `Cash('USD')`, `Cash('GBP')`, and `Cash('EUR')` preserve the provided currency
- `cash_like` is `True`

---

### `Equity`

**Source:** `qstrader/asset/equity.py`

`Equity` stores metadata for an equity instrument such as a common stock or ETF.

#### Constructor

```python
Equity(name, symbol, tax_exempt=True)
```

#### Parameters

- `name: str` — display name of the asset
- `symbol: str` — original ticker symbol
- `tax_exempt: bool` — whether the asset is exempt from transaction taxation rules

#### Attributes

- `cash_like: bool` — always set to `False`
- `name: str`
- `symbol: str`
- `tax_exempt: bool`

#### Representation

`Equity` implements `__repr__`, which returns a fully descriptive string:

```python
Equity(name='Apple, Inc.', symbol='AAPL', tax_exempt=True)
```

This is used directly in transaction-related tests.

#### Example

```python
from qstrader.asset.equity import Equity

spy = Equity('SPDR S&P 500 ETF Trust', 'SPY')
aapl = Equity('Apple, Inc.', 'AAPL', tax_exempt=False)
```

#### Notes

- The docstring notes that ticker mapping is still a TODO.
- The class is primarily a metadata object; portfolio and execution behavior live elsewhere in the codebase.

---

## Universe subpackage

The `qstrader.asset.universe` package defines interfaces and implementations for determining which assets are available at a particular timestamp.

This concept is used by multiple parts of QSTrader, including:

- alpha models
- signals
- portfolio construction
- trading sessions/backtests

The central interface is `Universe.get_assets(dt) -> list[str]`.

### `Universe`

**Source:** `qstrader/asset/universe/universe.py`

`Universe` is the abstract interface for all asset universes.

#### Method

```python
get_assets(dt) -> list[str]
```

#### Contract

Implementations must return the list of asset symbol strings that are in the universe at timestamp `dt`.

#### Important detail

Although the package also defines concrete asset objects such as `Equity`, universe implementations currently return **symbol strings**, not `Asset` instances.

Typical values look like:

- `EQ:SPY`
- `EQ:AGG`
- `EQ:GLD`

---

### `StaticUniverse`

**Source:** `qstrader/asset/universe/static.py`

`StaticUniverse` always returns the same list of assets, regardless of time.

#### Constructor

```python
StaticUniverse(asset_list)
```

#### Parameters

- `asset_list: list[str]` — fixed asset symbols in the universe

#### Method behavior

```python
get_assets(dt) -> list[str]
```

- Ignores the provided timestamp
- Returns the original `asset_list`

#### Example

```python
from qstrader.asset.universe.static import StaticUniverse

universe = StaticUniverse(['EQ:SPY', 'EQ:AGG'])
assets = universe.get_assets(dt)
# ['EQ:SPY', 'EQ:AGG']
```

#### Observed test coverage

Unit tests confirm that the same asset list is returned for different timestamps.

#### Typical usage

`StaticUniverse` is the most common universe in the repository examples, including buy-and-hold and 60/40 backtests.

---

### `DynamicUniverse`

**Source:** `qstrader/asset/universe/dynamic.py`

`DynamicUniverse` allows assets to appear in the universe only after a configured entry date.

#### Constructor

```python
DynamicUniverse(asset_dates)
```

#### Parameters

- `asset_dates: dict[str, pd.Timestamp]` — mapping from asset symbol to entry timestamp

#### Method behavior

```python
get_assets(dt) -> list[str]
```

Returns all assets satisfying both conditions:

1. the asset has a non-`None` entry date
2. `dt >= asset_date`

#### Example

```python
import pandas as pd
import pytz
from qstrader.asset.universe.dynamic import DynamicUniverse

universe = DynamicUniverse({
    'EQ:SPY': pd.Timestamp('1993-01-01 14:30:00', tz=pytz.UTC),
    'EQ:AGG': pd.Timestamp('2003-01-01 14:30:00', tz=pytz.UTC),
})

assets_1995 = universe.get_assets(pd.Timestamp('1995-01-01 14:30:00', tz=pytz.UTC))
# ['EQ:SPY']
```

#### Observed test coverage

Unit tests cover these cases:

- before every entry date: returns `[]`
- after only the first asset enters: returns that asset
- after multiple entry dates: returns all eligible assets

#### Current limitation

The module docstring explicitly notes that removal of assets is not yet supported. The design currently assumes a universe can expand over time, but not shrink.

---

## Symbol conventions

Within this repository, universes and several data-handling components use string symbols prefixed by an asset-class code.

Common examples include:

- `EQ:SPY`
- `EQ:AGG`
- `EQ:GLD`

The CSV data source in `qstrader/data/daily_bar_csv.py` currently constructs symbols in this form by mapping a filename like `SPY.csv` to `EQ:SPY`.

A related implementation detail is that `CSVDailyBarDataSource` accepts an `asset_type` constructor argument, but its docstring notes that this is currently unused and the symbol conversion is hardcoded to equity-style symbols.

---

## How the package is used elsewhere

### 1. Backtests and examples

Repository examples commonly do the following:

1. define ticker symbols such as `['SPY', 'AGG']`
2. convert them into QSTrader asset symbols such as `['EQ:SPY', 'EQ:AGG']`
3. wrap them in a `StaticUniverse`
4. pass that universe into data handlers, alpha models, and trading sessions

Example pattern:

```python
strategy_symbols = ['SPY', 'AGG']
strategy_assets = ['EQ:%s' % symbol for symbol in strategy_symbols]
strategy_universe = StaticUniverse(strategy_assets)
```

### 2. Signals

Signal classes store the universe and initialize their internal asset buffers with:

```python
self.assets = self.universe.get_assets(start_dt)
```

Signals also support dynamic universe expansion by checking for new assets at later timestamps.

### 3. Portfolio construction

Portfolio construction merges:

- the assets currently held in the broker portfolio
- the assets currently returned by the universe

This allows target allocations to consider both existing positions and currently tradable assets.

### 4. Transactions

Transaction tests demonstrate that `Equity` objects can be embedded directly in trade records and represented cleanly via `repr(...)`.

---

## Design observations

The current `qstrader.asset` package is intentionally simple and acts more as a **type and symbol-definition layer** than a full security master.

### Strengths

- clear separation between asset metadata and trading logic
- simple, readable universe abstractions
- enough structure to support static and gradually expanding backtests

### Current limitations

- `Asset` does not yet define a richer shared interface
- `Cash` and `Equity` are metadata containers only
- universes return symbol strings rather than rich asset objects
- `DynamicUniverse` supports additions only, not removals
- CSV asset symbol generation is currently hardcoded to equity-style `EQ:` symbols
- package `__init__` modules do not currently re-export public classes

---

## Quick reference

| Class | Module | Purpose | Key API |
|---|---|---|---|
| `Asset` | `qstrader.asset.asset` | Base asset type | inheritance root |
| `Cash` | `qstrader.asset.cash` | Cash-like asset metadata | `Cash(currency='USD')` |
| `Equity` | `qstrader.asset.equity` | Equity/ETF metadata | `Equity(name, symbol, tax_exempt=True)` |
| `Universe` | `qstrader.asset.universe.universe` | Abstract universe interface | `get_assets(dt)` |
| `StaticUniverse` | `qstrader.asset.universe.static` | Fixed symbol universe | `get_assets(dt)` |
| `DynamicUniverse` | `qstrader.asset.universe.dynamic` | Time-varying expanding universe | `get_assets(dt)` |

---

## Minimal usage examples

### Create asset objects

```python
from qstrader.asset.cash import Cash
from qstrader.asset.equity import Equity

cash = Cash('USD')
spy = Equity('SPDR S&P 500 ETF Trust', 'SPY')
```

### Create a static universe

```python
from qstrader.asset.universe.static import StaticUniverse

universe = StaticUniverse(['EQ:SPY', 'EQ:AGG'])
```

### Create a dynamic universe

```python
import pandas as pd
import pytz
from qstrader.asset.universe.dynamic import DynamicUniverse

universe = DynamicUniverse({
    'EQ:SPY': pd.Timestamp('1993-01-01 14:30:00', tz=pytz.UTC),
    'EQ:AGG': pd.Timestamp('2003-01-01 14:30:00', tz=pytz.UTC),
})
```

---

## Summary

`qstrader.asset` provides the foundational asset metadata classes and asset-universe abstractions used by the wider QSTrader backtesting framework. In its current form, it is best understood as a small, practical layer that:

- distinguishes cash-like vs non-cash assets,
- stores lightweight equity metadata,
- and controls time-dependent asset availability through universe objects.

For users working with this repository today, the most important operational detail is that many downstream systems consume **universe symbol strings** like `EQ:SPY`, while `Equity` and `Cash` remain useful metadata containers for object-level workflows such as transactions.

