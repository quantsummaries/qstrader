# `qstrader.broker`

## Overview

The `qstrader.broker` package implements the **brokerage simulation layer** for QSTrader. It manages account cash, sub-portfolios, open orders, trade execution, position accounting, transaction costs, and a full portfolio event history.

The package is built around three orthogonal concerns:

- **Account & order management** — `Broker` / `SimulatedBroker`
- **Portfolio & position accounting** — `Portfolio`, `Position`, `PositionHandler`, `PortfolioEvent`
- **Transaction cost modelling** — `FeeModel`, `ZeroFeeModel`, `PercentFeeModel`

A `Transaction` value object ties the two layers together.

---

## Package layout

```text
qstrader/broker/
├── __init__.py
├── broker.py
├── simulated_broker.py
├── fee_model/
│   ├── __init__.py
│   ├── fee_model.py
│   ├── percent_fee_model.py
│   └── zero_fee_model.py
├── portfolio/
│   ├── __init__.py
│   ├── portfolio.py
│   ├── portfolio_event.py
│   ├── position.py
│   └── position_handler.py
└── transaction/
    ├── __init__.py
    └── transaction.py
```

All `__init__.py` files are currently empty; imports are made from the concrete module paths.

---

## High-level design

```
SimulatedBroker
 ├── cash_balances          dict[currency → float]
 ├── portfolios             dict[portfolio_id → Portfolio]
 │    └── Portfolio
 │         ├── cash         float
 │         ├── history      list[PortfolioEvent]
 │         └── pos_handler  PositionHandler
 │              └── positions  OrderedDict[asset → Position]
 └── open_orders            dict[portfolio_id → Queue[Order]]
```

On each call to `SimulatedBroker.update(dt)`:
1. All position market values are refreshed using mid-prices from the data handler.
2. If the exchange is open, every queued order is executed against the portfolio.

---

## `Broker`

**Source:** `qstrader/broker/broker.py`

Abstract interface that both simulated and (future) live brokers implement. This ensures strategy logic is identical regardless of execution environment.

### Abstract methods

| Method | Signature | Purpose |
|---|---|---|
| `subscribe_funds_to_account` | `(amount)` | Credit cash to the master account |
| `withdraw_funds_from_account` | `(amount)` | Debit cash from the master account |
| `get_account_cash_balance` | `(currency=None)` | Full balance dict, or scalar for one currency |
| `get_account_total_equity` | `()` | Total equity across all portfolios |
| `create_portfolio` | `(portfolio_id, name)` | Create a named sub-portfolio |
| `list_all_portfolios` | `()` | Sorted list of all Portfolio instances |
| `subscribe_funds_to_portfolio` | `(portfolio_id, amount)` | Move cash from master → portfolio |
| `withdraw_funds_from_portfolio` | `(portfolio_id, amount)` | Move cash from portfolio → master |
| `get_portfolio_cash_balance` | `(portfolio_id)` | Cash balance of one portfolio |
| `get_portfolio_total_equity` | `(portfolio_id)` | Total equity of one portfolio |
| `get_portfolio_as_dict` | `(portfolio_id)` | Holdings as a nested dict |
| `submit_order` | `(portfolio_id, order)` | Queue an order for execution |

---

## `SimulatedBroker`

**Source:** `qstrader/broker/simulated_broker.py`

The only concrete `Broker` implementation in the current codebase. Simulates a multi-currency, multi-portfolio brokerage account with pluggable transaction costs.

### Constructor

```python
SimulatedBroker(
    start_dt,
    exchange,
    data_handler,
    account_id=None,
    base_currency='USD',
    initial_funds=0.0,
    fee_model=ZeroFeeModel(),
    slippage_model=None,          # TODO: not yet implemented
    market_impact_model=None      # TODO: not yet implemented
)
```

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `start_dt` | `pd.Timestamp` | Simulation start datetime |
| `exchange` | `Exchange` | Used to check if the venue is open for order execution |
| `data_handler` | `DataHandler` | Provides latest bid/ask/mid prices |
| `account_id` | `str` | Optional human-readable account identifier |
| `base_currency` | `str` | Account denomination; must be in `settings.SUPPORTED['CURRENCIES']` |
| `initial_funds` | `float` | Opening cash (non-negative) |
| `fee_model` | `FeeModel` | Commission and tax model; defaults to `ZeroFeeModel` |
| `slippage_model` | — | Placeholder; not yet active |
| `market_impact_model` | — | Placeholder; not yet active |

### Stored attributes

- `start_dt`, `current_dt`, `exchange`, `data_handler`, `account_id`
- `base_currency`, `initial_funds`, `fee_model`
- `cash_balances: dict[str, float]` — one entry per supported currency
- `portfolios: dict[str, Portfolio]` — keyed by portfolio ID
- `open_orders: dict[str, queue.Queue]` — one FIFO queue per portfolio

### Public methods

#### Account cash management

```python
subscribe_funds_to_account(amount)   # adds to cash_balances[base_currency]
withdraw_funds_from_account(amount)  # subtracts; raises ValueError if insufficient
get_account_cash_balance(currency=None)
    # → dict[str, float]  if currency is None
    # → float             if a currency code is passed
get_account_total_equity()
    # → dict{portfolio_id: equity, ..., 'master': total}
get_account_total_market_value()
    # → dict{portfolio_id: market_value, ..., 'master': total}
```

#### Portfolio lifecycle

```python
create_portfolio(portfolio_id, name=None)   # raises ValueError on duplicate ID
list_all_portfolios()                        # → list[Portfolio], sorted by ID
```

#### Portfolio cash management

```python
subscribe_funds_to_portfolio(portfolio_id, amount)
    # deducts from master cash_balances; credits portfolio
withdraw_funds_from_portfolio(portfolio_id, amount)
    # deducts from portfolio; credits master cash_balances
get_portfolio_cash_balance(portfolio_id)    # → float
get_portfolio_total_equity(portfolio_id)    # → float
get_portfolio_total_market_value(portfolio_id)  # → float
get_portfolio_as_dict(portfolio_id)         # → dict (see Portfolio.portfolio_to_dict)
```

#### Order submission and execution

```python
submit_order(portfolio_id, order)
    # puts order onto the FIFO queue for portfolio_id
```

#### Simulation loop

```python
update(dt)
```

Called once per simulation tick:

1. Advances `current_dt` to `dt`.
2. Refreshes position market values via `data_handler.get_asset_latest_mid_price(dt, asset)`.
3. If `exchange.is_open_at_datetime(dt)` is `True`, drains all order queues, sorts orders by direction (short sales first), then calls `_execute_order` for each.

#### Order execution (internal)

```python
_execute_order(dt, portfolio_id, order)
```

- Fetches bid/ask pair from `data_handler.get_asset_latest_bid_ask_price(dt, asset)`.
- Uses **ask price** for buy orders, **bid price** for sell orders.
- Computes consideration = `price × quantity` (rounded to nearest integer).
- Calls `fee_model.calc_total_cost(asset, quantity, consideration, broker)` for commission.
- If the estimated cost exceeds portfolio cash, logs a **warning but still executes** (portfolio cash can go negative).
- Constructs a `Transaction` and passes it to `Portfolio.transact_asset(txn)`.

### Validation rules

| Condition | Behaviour |
|---|---|
| Unsupported `base_currency` | `ValueError` on construction |
| Negative `initial_funds` | `ValueError` on construction |
| Non-`FeeModel` subclass | `TypeError` on construction |
| Negative credit/debit amounts | `ValueError` |
| Withdrawing more than available | `ValueError` |
| Duplicate portfolio ID | `ValueError` |
| Unknown portfolio ID on order | `KeyError` |
| No price available for asset | `ValueError` (order not executed) |

---

## Fee models

### `FeeModel`

**Source:** `qstrader/broker/fee_model/fee_model.py`

Abstract base class for all transaction cost models.

```python
class FeeModel:
    @abstractmethod
    def _calc_commission(self, asset, quantity, consideration, broker=None) -> float: ...

    @abstractmethod
    def _calc_tax(self, asset, quantity, consideration, broker=None) -> float: ...

    @abstractmethod
    def calc_total_cost(self, asset, quantity, consideration, broker=None) -> float: ...
```

**Parameters shared by all fee model methods:**

| Parameter | Type | Description |
|---|---|---|
| `asset` | `str` | Asset symbol string |
| `quantity` | `int` | Quantity of assets traded |
| `consideration` | `float` | `price × quantity` (total notional) |
| `broker` | `Broker` | Optional reference to the broker, for advanced models |

---

### `ZeroFeeModel`

**Source:** `qstrader/broker/fee_model/zero_fee_model.py`

The default fee model. Returns `0.0` for every cost component.

```python
ZeroFeeModel()
```

Suitable for cost-free backtests or as a baseline when comparing strategy performance with and without fees.

---

### `PercentFeeModel`

**Source:** `qstrader/broker/fee_model/percent_fee_model.py`

Calculates commission and stamp duty as a fixed percentage of the absolute consideration.

```python
PercentFeeModel(commission_pct=0.0, tax_pct=0.0)
```

#### Parameters

| Parameter | Type | Description |
|---|---|---|
| `commission_pct` | `float` | Commission as a decimal fraction; `0.001` = 0.1% |
| `tax_pct` | `float` | Tax (e.g. stamp duty) as a decimal fraction; `0.005` = 0.5% |

#### Calculation

```text
commission = commission_pct × |consideration|
tax        = tax_pct        × |consideration|
total      = commission + tax
```

The absolute value of consideration ensures the same percentage applies symmetrically to buys and sells.

#### Example

```python
from qstrader.broker.fee_model.percent_fee_model import PercentFeeModel

# 0.1% commission, 0.5% stamp duty
fee_model = PercentFeeModel(commission_pct=0.001, tax_pct=0.005)
```

This is the pattern used in `examples/sixty_forty_fees.py`.

---

## `Transaction`

**Source:** `qstrader/broker/transaction/transaction.py`

Immutable value object representing a single trade execution. Created by `SimulatedBroker._execute_order` and consumed by `Portfolio.transact_asset`.

### Constructor

```python
Transaction(
    asset,           # str   — asset symbol
    quantity,        # int   — positive = buy, negative = sell
    dt,              # pd.Timestamp
    price,           # float — execution price
    order_id,        # int   — unique identifier from the originating Order
    commission=0.0   # float — total commission charged
)
```

### Attributes

- `asset`, `quantity`, `dt`, `price`, `order_id`, `commission`
- `direction: float` — `+1.0` (buy) or `-1.0` (sell), derived via `np.copysign(1, quantity)`

### Properties

| Property | Formula | Description |
|---|---|---|
| `cost_without_commission` | `quantity × price` | Raw notional cost |
| `cost_with_commission` | `cost_without_commission + commission` | Total cost including fees |

### Representation

`__repr__` returns a string that can be used to recreate the object:

```text
Transaction(asset=EQ:SPY, quantity=100, dt=2019-01-01 15:00:00+00:00, price=250.0, order_id=1)
```

---

## Portfolio subsystem

### `PortfolioEvent`

**Source:** `qstrader/broker/portfolio/portfolio_event.py`

An immutable audit-trail record representing one change to portfolio cash.

### Constructor

```python
PortfolioEvent(dt, type, description, debit, credit, balance)
```

| Field | Type | Description |
|---|---|---|
| `dt` | `datetime` | When the event occurred |
| `type` | `str` | `'subscription'`, `'withdrawal'`, or `'asset_transaction'` |
| `description` | `str` | Human-readable summary |
| `debit` | `float` | Amount debited from cash |
| `credit` | `float` | Amount credited to cash |
| `balance` | `float` | Cash balance after the event |

### Factory class methods

```python
PortfolioEvent.create_subscription(dt, credit, balance)
PortfolioEvent.create_withdrawal(dt, debit, balance)
```

Both round `credit`/`debit` and `balance` to 2 decimal places.

### Other methods

- `__eq__(other)` — field-by-field equality
- `__repr__()` — readable string
- `to_dict()` — converts to a plain dict (used by `Portfolio.history_to_df()`)

---

### `Position`

**Source:** `qstrader/broker/portfolio/position.py`

Tracks the full lifetime accounting of a single asset position, including separate long-side and short-side running averages and a realised/unrealised P&L split.

### Factory method (preferred construction)

```python
Position.open_from_transaction(transaction: Transaction) -> Position
```

Creates a new `Position` from the first `Transaction` for an asset.

### Direct constructor

```python
Position(
    asset,
    current_price,
    current_dt,
    buy_quantity,
    sell_quantity,
    avg_bought,
    avg_sold,
    buy_commission,
    sell_commission
)
```

### Key properties

| Property | Description |
|---|---|
| `net_quantity` | `buy_quantity − sell_quantity` |
| `direction` | `+1` (long), `0` (flat), `-1` (short) |
| `market_value` | `current_price × net_quantity` |
| `avg_price` | Average entry price on the active side, including commission |
| `total_bought` | `avg_bought × buy_quantity` |
| `total_sold` | `avg_sold × sell_quantity` |
| `net_total` | `total_sold − total_bought` |
| `commission` | `buy_commission + sell_commission` |
| `net_incl_commission` | `net_total − commission` |
| `unrealised_pnl` | `(current_price − avg_price) × net_quantity` |
| `realised_pnl` | P&L from opposing trades (commission-adjusted, proportional allocation) |
| `total_pnl` | `realised_pnl + unrealised_pnl` |

#### Average price detail

`avg_price` accounts for commissions in the cost basis:

```text
Long:  (avg_bought × buy_quantity + buy_commission) / buy_quantity
Short: (avg_sold × sell_quantity − sell_commission) / sell_quantity
```

#### Realised P&L calculation

For a **long** position that has been partially sold:

```text
realised_pnl =
    (avg_sold − avg_bought) × sell_quantity
    − (sell_quantity / buy_quantity) × buy_commission
    − sell_commission
```

For a **short** position that has been partially covered:

```text
realised_pnl =
    (avg_sold − avg_bought) × buy_quantity
    − (buy_quantity / sell_quantity) × sell_commission
    − buy_commission
```

When the position is fully flat (`direction == 0`), `realised_pnl` equals `net_incl_commission`.

### Methods

```python
update_current_price(market_price, dt=None)
    # Updates current_price; validates positive price and monotonic time

transact(transaction: Transaction)
    # Applies a new trade; dispatches to _transact_buy or _transact_sell
    # Rejects transactions for a different asset
    # No-op if transaction quantity rounds to 0
```

### Timestamp invariant

All time updates are validated — any attempt to move the position backward in time raises a `ValueError`.

---

### `PositionHandler`

**Source:** `qstrader/broker/portfolio/position_handler.py`

Manages the collection of `Position` objects for a single portfolio.

### Constructor

```python
PositionHandler()
# → self.positions: OrderedDict[str, Position]  (empty)
```

### Methods

```python
transact_position(transaction: Transaction)
    # Creates a new Position if the asset is unseen,
    # otherwise calls position.transact(transaction).
    # Automatically deletes the position if net_quantity reaches 0.

total_market_value() -> float
total_unrealised_pnl() -> float
total_realised_pnl() -> float
total_pnl() -> float
    # All return 0.0 when positions is empty.
```

Insertion order is preserved via `OrderedDict`.

---

### `Portfolio`

**Source:** `qstrader/broker/portfolio/portfolio.py`

Combines a cash balance, a `PositionHandler`, and a `PortfolioEvent` history into a single entity. Created and owned by `SimulatedBroker`.

### Constructor

```python
Portfolio(
    start_dt,
    starting_cash=0.0,
    currency='USD',
    portfolio_id=None,
    name=None
)
```

Initialisation appends a `PortfolioEvent.create_subscription` event to `history` when `starting_cash > 0`.

### Attributes

| Attribute | Type | Description |
|---|---|---|
| `start_dt`, `current_dt` | `pd.Timestamp` | Creation and current time |
| `starting_cash` | `float` | Opening cash |
| `cash` | `float` | Current cash balance |
| `currency`, `portfolio_id`, `name` | `str` | Metadata |
| `pos_handler` | `PositionHandler` | Manages all positions |
| `history` | `list[PortfolioEvent]` | Full audit trail |

### Properties

| Property | Description |
|---|---|
| `total_market_value` | Sum of all position market values (excludes cash) |
| `total_equity` | `total_market_value + cash` |
| `total_unrealised_pnl` | Sum of all position unrealised P&Ls |
| `total_realised_pnl` | Sum of all position realised P&Ls |
| `total_pnl` | `total_unrealised_pnl + total_realised_pnl` |

### Methods

```python
subscribe_funds(dt, amount)
    # Credits cash; appends subscription PortfolioEvent.
    # Raises ValueError if dt < current_dt or amount < 0.

withdraw_funds(dt, amount)
    # Debits cash; appends withdrawal PortfolioEvent.
    # Raises ValueError if dt < current_dt, amount < 0, or amount > cash.

transact_asset(txn: Transaction)
    # Passes txn to pos_handler.transact_position(txn).
    # Deducts (price × quantity + commission) from cash.
    # Logs a warning (but proceeds) if cash goes negative.
    # Appends an asset_transaction PortfolioEvent.
    # Raises ValueError if txn.dt < current_dt.

update_market_value_of_asset(asset, current_price, current_dt)
    # Calls pos_handler.positions[asset].update_current_price(...).
    # No-op if asset not in positions.
    # Raises ValueError if current_price < 0 or current_dt < current_dt.

portfolio_to_dict() -> dict
    # Returns {asset: {quantity, market_value, unrealised_pnl, realised_pnl, total_pnl}}
    # for all open positions (excludes cash).

history_to_df() -> pd.DataFrame
    # Converts history to a DataFrame indexed by date with columns:
    # type, description, debit, credit, balance.
```

### Temporal monotonicity

Every `Portfolio` operation that accepts a `dt` argument requires `dt >= current_dt`. This guarantees that the event history and position timestamps are always in ascending order.

---

## Data flow during a backtest

```
BacktestTradingSession
  └── QuantTradingSystem.__call__(dt)
       └── PortfolioConstructionModel.__call__(dt)
            └── ExecutionHandler.generate_orders(rebalance_orders)
                 └── SimulatedBroker.submit_order(portfolio_id, order)
                      ↓ (queued)
SimulatedBroker.update(dt)        ← called each simulation tick
  ├── refresh position prices via data_handler
  └── if exchange.is_open:
       └── _execute_order(dt, portfolio_id, order)
            ├── fetch bid/ask from data_handler
            ├── compute consideration + fee_model.calc_total_cost(...)
            ├── create Transaction(...)
            └── Portfolio.transact_asset(txn)
                 ├── PositionHandler.transact_position(txn)
                 │    └── Position.transact(txn)  or  Position.open_from_transaction(txn)
                 └── append PortfolioEvent to history
```

---

## How the broker is wired in a backtest

`BacktestTradingSession` creates and configures the broker in `_create_broker()`:

```python
broker = SimulatedBroker(
    self.start_dt,
    self.exchange,
    self.data_handler,
    account_id=self.account_id,
    base_currency='USD',
    initial_funds=self.initial_cash,
    fee_model=self.fee_model
)
broker.subscribe_funds_to_account(self.initial_cash)
broker.create_portfolio(portfolio_id=self.portfolio_id, name=self.portfolio_name)
broker.subscribe_funds_to_portfolio(self.portfolio_id, self.initial_cash)
```

The default `fee_model` is `ZeroFeeModel()`. To add transaction costs, pass a `PercentFeeModel` instance:

```python
from qstrader.broker.fee_model.percent_fee_model import PercentFeeModel

fee_model = PercentFeeModel(commission_pct=0.001, tax_pct=0.005)
session = BacktestTradingSession(..., fee_model=fee_model)
```

---

## Observed test coverage

Unit tests in `tests/unit/broker/` cover:

| File | Classes / scenarios tested |
|---|---|
| `test_simulated_broker.py` | 30+ tests: account/portfolio funding, order queuing/execution, equity/market value aggregation, validation errors |
| `portfolio/test_portfolio.py` | 15+ tests: fund subscriptions, withdrawals, transactions, datetime monotonicity, `portfolio_to_dict` |
| `portfolio/test_position.py` | 12+ tests: long/short accounting, partial closes, P&L calculations, commission allocation |
| `portfolio/test_position_handler.py` | 6 tests: open/close/reopen, aggregated totals |
| `fee_model/test_zero_fee_model.py` | Zero-cost assertion |
| `fee_model/test_percent_fee_model.py` | 6 parametrized tests for commission and tax |
| `transaction/test_transaction.py` | Transaction creation and repr |

---

## Design notes and limitations

- **Slippage and market impact** — `slippage_model` and `market_impact_model` parameters are accepted but not yet implemented (`TODO` in source).
- **Buy price = ask, sell price = bid** — price selection is based on order direction; with the current `CSVDailyBarDataSource` bid and ask are identical, so there is no real spread in practice.
- **Negative cash is allowed** — both `SimulatedBroker._execute_order` and `Portfolio.transact_asset` warn but proceed if the transaction would leave the portfolio with negative cash.
- **Short sales executed first** — `SimulatedBroker.update` sorts orders by direction so that short sales (which free up cash) run before new buys.
- **No settlement delay** — cash is exchanged immediately on execution.
- **Multi-currency accounting** — `cash_balances` tracks all supported currencies, but all portfolio operations are denominated in `base_currency`.

---

## Quick reference

| Class | Module | Purpose |
|---|---|---|
| `Broker` | `qstrader.broker.broker` | Abstract broker interface |
| `SimulatedBroker` | `qstrader.broker.simulated_broker` | Full simulated broker implementation |
| `FeeModel` | `qstrader.broker.fee_model.fee_model` | Abstract transaction cost interface |
| `ZeroFeeModel` | `qstrader.broker.fee_model.zero_fee_model` | Zero-cost fee model (default) |
| `PercentFeeModel` | `qstrader.broker.fee_model.percent_fee_model` | Percentage commission + tax model |
| `Transaction` | `qstrader.broker.transaction.transaction` | Single trade execution record |
| `Portfolio` | `qstrader.broker.portfolio.portfolio` | Cash + positions + history |
| `PortfolioEvent` | `qstrader.broker.portfolio.portfolio_event` | Immutable cash-change audit record |
| `Position` | `qstrader.broker.portfolio.position` | Per-asset accounting with P&L |
| `PositionHandler` | `qstrader.broker.portfolio.position_handler` | Collection of Position objects |

---

## Minimal usage examples

### Create a broker and fund a portfolio

```python
import pandas as pd
import pytz
from unittest.mock import Mock

from qstrader.broker.simulated_broker import SimulatedBroker
from qstrader.broker.fee_model.zero_fee_model import ZeroFeeModel

start_dt = pd.Timestamp('2019-01-01 14:30:00', tz=pytz.UTC)
exchange = Mock()
exchange.is_open_at_datetime.return_value = True
data_handler = Mock()

broker = SimulatedBroker(
    start_dt, exchange, data_handler,
    account_id='my_account',
    initial_funds=100_000.0,
    fee_model=ZeroFeeModel()
)

broker.create_portfolio(portfolio_id='001', name='Main Strategy')
broker.subscribe_funds_to_portfolio('001', 100_000.0)

print(broker.get_portfolio_cash_balance('001'))  # 100000.0
```

### Apply percentage transaction costs

```python
from qstrader.broker.fee_model.percent_fee_model import PercentFeeModel

# 0.1% commission, 0.5% tax
fee_model = PercentFeeModel(commission_pct=0.001, tax_pct=0.005)

# Pass to BacktestTradingSession:
session = BacktestTradingSession(
    start_dt, end_dt, universe, alpha_model,
    fee_model=fee_model,
    ...
)
```

### Inspect position P&L

```python
holdings = broker.get_portfolio_as_dict('001')
for asset, data in holdings.items():
    print(asset, data['net_quantity'], data['unrealised_pnl'], data['realised_pnl'])
```

### Export event history to a DataFrame

```python
portfolio = broker.portfolios['001']
df = portfolio.history_to_df()
print(df.head())
```

---

## Summary

`qstrader.broker` is QSTrader's complete brokerage simulation layer. Its key design decisions are:

- A clean `Broker` abstract interface ensures strategy code is agnostic to simulated vs. live execution.
- `SimulatedBroker` handles account cash, sub-portfolio lifecycle, order queuing, and FIFO execution.
- Pluggable `FeeModel` implementations make it easy to compare zero-cost and realistic cost scenarios.
- `Portfolio` and `Position` maintain a full, time-ordered accounting trail including realised/unrealised P&L and a portfolio event history.
- All temporal operations enforce monotonic timestamps, preventing accidental out-of-order data.

