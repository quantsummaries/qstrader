# `qstrader.data`

## Overview

The `qstrader.data` package provides the market-data layer used by the backtesting components in this repository. In the current codebase it is focused on **daily CSV OHLCV data** and exposes two main building blocks:

- `CSVDailyBarDataSource` in `qstrader/data/daily_bar_csv.py`
- `BacktestDataHandler` in `qstrader/data/backtest_data_handler.py`

Together they support a simple workflow:

1. load daily bar data from CSV files,
2. convert each daily bar into timestamped open/close price events,
3. expose bid/ask/mid lookup methods for the rest of the backtest,
4. optionally provide historical closing-price ranges for multi-asset analysis.

This package is intentionally lightweight and currently optimized for **daily end-of-day style backtests**, not full intraday market microstructure.

---

## Package layout

```text
qstrader/data/
├── __init__.py
├── backtest_data_handler.py
└── daily_bar_csv.py
```

`qstrader/data/__init__.py` is currently empty, so imports are generally done from the concrete module paths.

---

## Design summary

### Main responsibilities

- **`CSVDailyBarDataSource`**
  - loads CSV files from disk,
  - parses and localizes dates to UTC,
  - converts daily OHLCV bars into open/close timestamped prices,
  - serves per-asset bid/ask queries.

- **`BacktestDataHandler`**
  - wraps one or more data sources,
  - tries each source in order until it finds valid price data,
  - exposes a simpler interface to the rest of the system.

### Symbol convention

The data package uses QSTrader-style asset symbol strings such as:

- `EQ:SPY`
- `EQ:AGG`
- `EQ:GLD`

A CSV filename like `SPY.csv` is converted into the asset symbol `EQ:SPY`.

### Time convention

Daily bars are turned into two intraday timestamps:

- **Open** → `14:30 UTC`
- **Close** → `21:00 UTC`

These timestamps correspond to the market open and close assumptions used by the backtester.

---

## `CSVDailyBarDataSource`

**Source:** `qstrader/data/daily_bar_csv.py`

### Purpose

`CSVDailyBarDataSource` encapsulates loading, preparing, and querying daily OHLCV CSV files.

Its core idea is that daily bars are not consumed directly. Instead, each bar is transformed into a small price timeline with two entries per trading day:

- one at the assumed market open,
- one at the assumed market close.

This allows other parts of the system to query “latest bid/ask” at a timestamp during a daily backtest.

### Constructor

```text
CSVDailyBarDataSource(csv_dir, asset_type, adjust_prices=True, csv_symbols=None)
```

### Parameters

- `csv_dir: str`
  - Directory containing the CSV files.
- `asset_type`
  - Asset type metadata passed in by callers.
  - In the current implementation this value is stored but not used for symbol generation or behavior.
- `adjust_prices: bool = True`
  - If `True`, adjusted prices are derived from the CSV `Adj Close` column.
- `csv_symbols: list[str] | None = None`
  - Optional list of symbols to load.
  - If omitted, all `.csv` files in the directory are loaded.

### Important note about `asset_type`

The class docstring explicitly notes that `asset_type` is currently unused. This is visible in repository examples as well:

- some callers pass `Equity`
- some callers pass `'Equity'`

Both work because the current implementation does not act on this argument.

---

### Internal data structures

The constructor immediately builds two dictionaries:

- `self.asset_bar_frames`
  - raw daily bar DataFrames keyed by asset symbol
- `self.asset_bid_ask_frames`
  - converted timestamped price DataFrames keyed by asset symbol

So initialization performs all CSV loading and conversion upfront.

---

### File discovery

#### `_obtain_asset_csv_files() -> list[str]`

Returns every filename in `csv_dir` ending in `.csv`.

#### `_obtain_asset_symbol_from_filename(csv_file) -> str`

Maps a CSV filename to a QSTrader asset symbol.

Example:

```text
'SPY.csv' -> 'EQ:SPY'
```

#### Current limitation

This mapping is hardcoded to the `EQ:` prefix, so the implementation currently assumes equity-style assets.

---

### CSV loading

#### `_load_csv_into_df(csv_file)`

Loads a CSV into a Pandas DataFrame by:

- reading the file with `Date` as the index,
- parsing dates,
- sorting by index,
- localizing the index to UTC.

The expected CSV format matches the repository sample data, for example:

```text
Date,Adj Close,Close,High,Low,Open,Volume
1993-01-29,24.113256454467773,43.9375,43.96875,43.75,43.96875,1003200
```

#### Expected columns

At minimum, the pricing conversion logic expects:

- `Open`
- `Close`

And when `adjust_prices=True`:

- `Adj Close`

---

### Bulk CSV loading

#### `_load_csvs_into_dfs()`

This method determines which files to load:

- if `csv_symbols` is provided, it constructs filenames like `SPY.csv`, `AGG.csv`
- otherwise it loads all CSV files in `csv_dir`

It then creates a dictionary:

```text
{
    'EQ:SPY': <DataFrame>,
    'EQ:AGG': <DataFrame>,
    ...
}
```

#### Logging behavior

If `qstrader.settings.PRINT_EVENTS` is enabled, the loader prints progress messages while loading and converting files.

#### Current limitation

The code assumes that all requested `csv_symbols` exist in the directory. There is a TODO comment noting that this is not validated explicitly.

---

### Bar-to-price conversion

#### `_convert_bar_frame_into_bid_ask_df(bar_df)`

This is the most important transformation in the module.

Given a daily OHLCV DataFrame, it:

1. sorts by date,
2. optionally adjusts prices using `Adj Close`,
3. keeps only open and close price information,
4. transforms those values into separate timestamped rows,
5. creates a bid/ask DataFrame.

#### Adjusted price mode

If `adjust_prices=True`:

- the method requires an `Adj Close` column,
- it computes adjusted open as:

```text
Adj Open = (Adj Close / Close) * Open
```

- it then renames the adjusted columns back to `Open` and `Close`.

This allows both open and close to reflect corporate actions consistently.

#### Non-adjusted mode

If `adjust_prices=False`, the method simply uses the raw `Open` and `Close` columns.

---

### Intraday timestamp conversion

The transformed DataFrame assigns one row per open and one row per close.

The conversion uses:

- `Open` rows → `Date + 14:30`
- `Close` rows → `Date + 21:00`

The final converted frame contains:

- `Bid`
- `Ask`

indexed by the timestamped `Date` column.

### Important simplification

The current implementation sets:

```text
Bid = Price
Ask = Price
```

So there is **no real bid/ask spread modeling** yet. This is a deliberate simplification for daily-bar backtests.

---

### Converted data cache

#### `_convert_bars_into_bid_ask_dfs()`

Applies the bar-to-bid/ask transformation to every loaded asset and stores the results in `self.asset_bid_ask_frames`.

---

### Price query API

#### `get_bid(dt, asset)`

Returns the latest available bid price for an asset at timestamp `dt`.

Implementation details:

- uses `pandas.Index.get_indexer(..., method='pad')`
- returns the most recent known value at or before `dt`
- if the query is before the first available timestamp, returns `np.nan`

#### `get_ask(dt, asset)`

Same behavior as `get_bid`, but returns the ask column.

#### Performance note

Both `get_bid` and `get_ask` are wrapped with:

```text
@functools.lru_cache(maxsize=1024 * 1024)
```

This provides memoization for repeated price lookups during a backtest.

---

### Historical close range API

#### `get_assets_historical_closes(start_dt, end_dt, assets)`

Builds a multi-asset DataFrame of historical close prices:

- columns are asset symbols,
- rows are timestamps,
- only assets present in `self.asset_bar_frames` are included,
- the result is restricted to `start_dt:end_dt`.

Example shape:

```text
                           EQ:SPY    EQ:AGG
2003-09-30 00:00:00+00:00  ...       ...
2003-10-01 00:00:00+00:00  ...       ...
```

#### Behavior note

This method uses the raw `Close` column from the original bar frames, not the converted intraday bid/ask frames.

---

## `BacktestDataHandler`

**Source:** `qstrader/data/backtest_data_handler.py`

### Purpose

`BacktestDataHandler` acts as an adapter between the trading system and one or more underlying data sources.

Instead of the rest of QSTrader talking directly to a CSV loader, it queries the handler for:

- latest bid,
- latest ask,
- latest bid/ask pair,
- latest mid,
- historical close ranges.

### Constructor

```text
BacktestDataHandler(universe, data_sources=None)
```

### Parameters

- `universe`
  - The asset universe associated with the backtest.
- `data_sources`
  - A list of data sources to query in order.

### Stored attributes

- `self.universe`
- `self.data_sources`

---

### Multi-source lookup behavior

For latest-price queries, the handler loops through `self.data_sources` in order and returns the first non-NaN value it finds.

This allows a form of source fallback, although the repository examples generally use a single CSV data source.

---

### Methods

#### `get_asset_latest_bid_price(dt, asset_symbol)`

- tries each data source in order,
- calls `ds.get_bid(dt, asset_symbol)`,
- returns the first value that is not `np.nan`,
- otherwise returns `np.nan`.

The method swallows exceptions and continues to the next source.

#### `get_asset_latest_ask_price(dt, asset_symbol)`

Same logic as bid-price lookup, but using `ds.get_ask(...)`.

#### `get_asset_latest_bid_ask_price(dt, asset_symbol)`

Currently returns:

```text
(bid, bid)
```

not `(bid, ask)`.

This mirrors the package’s current assumption that daily OHLCV data effectively provides a single tradable price rather than a true spread.

#### `get_asset_latest_mid_price(dt, asset_symbol)`

Computes:

```text
(bid + ask) / 2.0
```

using the result of `get_asset_latest_bid_ask_price(...)`.

Because the current bid/ask pair is `(bid, bid)`, the mid price is effectively the same as the bid price in the present implementation.

#### `get_assets_historical_range_close_price(start_dt, end_dt, asset_symbols, adjusted=False)`

Attempts to request a historical closing-price DataFrame from each data source.

If a source returns a non-`None` DataFrame, it is returned immediately.

---

## Data flow through the backtester

The data package sits in the middle of the main backtesting pipeline.

### Typical flow

1. Build a universe such as `StaticUniverse(['EQ:SPY', 'EQ:AGG'])`
2. Create a CSV data source
3. Wrap it in a `BacktestDataHandler`
4. Pass the handler into a `BacktestTradingSession` or `SignalsCollection`
5. Let broker/signals/alpha components query prices through the handler

### Common example pattern

From repository examples:

```text
csv_dir = os.environ.get('QSTRADER_CSV_DATA_DIR', DATA_DIR)
data_source = CSVDailyBarDataSource(csv_dir, 'Equity', csv_symbols=['SPY', 'AGG'])
data_handler = BacktestDataHandler(strategy_universe, data_sources=[data_source])
```

Although one example passes `'Equity'` as a string, others pass the `Equity` class itself. This works because `asset_type` is not used by the current implementation.

---

## How `qstrader.data` is used elsewhere

### 1. Trading sessions

`qstrader/trading/backtest.py` creates a default CSV data source and wraps it in a `BacktestDataHandler` when a custom handler is not supplied.

This means `qstrader.data` is the default market-data path for straightforward backtests.

### 2. Broker valuation

`qstrader/broker/simulated_broker.py` calls:

```text
self.data_handler.get_asset_latest_mid_price(dt, asset)
```

when updating portfolio market values.

### 3. Signals

`qstrader/signals/signals_collection.py` uses the handler to fetch the latest mid price for each asset before appending that value to signal buffers.

### 4. Example strategies

The examples `buy_and_hold.py`, `long_short.py`, `sixty_forty.py`, `sixty_forty_fees.py`, `momentum_taa.py`, and `scripts/static_backtest.py` all use `CSVDailyBarDataSource` together with `BacktestDataHandler`.

---

## CSV expectations

Based on the repository sample files in `data/`, the expected CSV schema includes columns like:

```text
Date,Adj Close,Close,High,Low,Open,Volume
```

### Required columns by mode

#### Always required

- `Date`
- `Open`
- `Close`

#### Required only when `adjust_prices=True`

- `Adj Close`

If `adjust_prices=True` and `Adj Close` is missing, the loader raises a `ValueError`.

---

## Limitations and quirks

The current implementation is small and practical, but there are a few important caveats.

### 1. `asset_type` is stored but unused

The constructor accepts `asset_type`, but symbol generation is still hardcoded to equity-style symbols.

### 2. No true bid/ask spread handling

Bid and ask are currently identical. This is suitable for simple daily strategies, but not for realistic intraday or spread-sensitive modeling.

### 3. Open/close only

The converted timeline uses only open and close timestamps, not full intraday bars or tick data.

### 4. Assumes CSV files exist

When `csv_symbols` is specified, filenames are constructed directly without explicit existence checks.

### 5. Historical close interface mismatch

`BacktestDataHandler.get_assets_historical_range_close_price(...)` forwards an `adjusted` keyword argument to the data source:

```text
ds.get_assets_historical_closes(start_dt, end_dt, asset_symbols, adjusted=adjusted)
```

However, `CSVDailyBarDataSource.get_assets_historical_closes(...)` currently accepts only:

```text
(start_dt, end_dt, assets)
```

So this handler/source interface is not fully aligned in the current codebase. A workspace search shows no other direct caller of `get_assets_historical_range_close_price(...)`, suggesting this path may be unfinished or currently unused.

### 6. Sparse internal docstrings in `BacktestDataHandler`

Most method docstrings in `backtest_data_handler.py` are placeholders, so behavior is best understood from the code itself.

---

## Quick reference

| Class | Module | Purpose | Key methods |
|---|---|---|---|
| `CSVDailyBarDataSource` | `qstrader.data.daily_bar_csv` | Load and convert daily CSV bars into timestamped price series | `get_bid`, `get_ask`, `get_assets_historical_closes` |
| `BacktestDataHandler` | `qstrader.data.backtest_data_handler` | Coordinate one or more data sources for backtests | `get_asset_latest_bid_price`, `get_asset_latest_ask_price`, `get_asset_latest_mid_price` |

---

## Minimal usage examples

### Load a subset of CSV symbols

```text
from qstrader.asset.equity import Equity
from qstrader.data.daily_bar_csv import CSVDailyBarDataSource

csv_source = CSVDailyBarDataSource(
    csv_dir='data',
    asset_type=Equity,
    csv_symbols=['SPY', 'AGG']
)
```

### Wrap the source in a handler

```text
from qstrader.asset.universe.static import StaticUniverse
from qstrader.data.backtest_data_handler import BacktestDataHandler

universe = StaticUniverse(['EQ:SPY', 'EQ:AGG'])
data_handler = BacktestDataHandler(universe, data_sources=[csv_source])
```

### Query the latest price

```text
bid = data_handler.get_asset_latest_bid_price(dt, 'EQ:SPY')
mid = data_handler.get_asset_latest_mid_price(dt, 'EQ:SPY')
```

### Obtain historical closes directly from the CSV source

```text
closes = csv_source.get_assets_historical_closes(
    start_dt,
    end_dt,
    ['EQ:SPY', 'EQ:AGG']
)
```

---

## Summary

`qstrader.data` is the repository’s core backtest data-access layer for daily CSV-based strategies. It is designed around a simple but effective model:

- load daily OHLCV data from disk,
- convert each trading day into open/close price events,
- expose cached price lookup methods,
- and provide a thin handler abstraction for the rest of the system.

For the current repository, the most important practical details are:

- symbols are expected in the form `EQ:SYMBOL`,
- CSV data is treated as equity-style data,
- bid and ask are currently identical,
- and `CSVDailyBarDataSource` plus `BacktestDataHandler` form the default data path used by the example backtests.


