# Testing and Documentation

## alpha_model

- [x] alpha_model.py::AlphaModel, abstract class that defines the interface for an alpha model.
  - fixed_signals.py::FixedSignalsAlphaModel, subclass of AlphaModel that returns a fixed dictionary of signal weights.
  - single_signal.py::SingleSignalAlphaModel, subclass of AlphaModel that applies one scalar signal to all current universe assets.
  
- [x] tests -> unit -> alpha_model

## asset

- [x] asset.py::Asset, abstract class that stores meta data about a trading asset.
  - cash.py::Cash, subclass of Asset that represents cash as a trading asset.
  - equity.py::Equity, subclass of Asset that stores meta data about an equity common stock or ETF.

- [x] universe.py::Universe, interface specification for an Asset Universe. 
  - dynamic.py::DynamicUniverse, subclass of Universe that that allows additions of assets beyond a certain datetime.
  - static.py::StaticUniverse, subclass of Universe that does not change its composition through time.

- [x] tests -> unit -> asset

## TODO: broker

## data

- [x] backtest_data_handler.py::BacktestDataHandler, provides an asset's latest bid, ask, and mid prices, as well as the historical range close prices. 
- [x] daily_bar_csv.py::CSVDailyBarDataSource, encapsulates loading, preparation and querying of CSV files of daily 'bar' OHLCV data. The CSV files are converted into a intraday
    timestamped Pandas DataFrame with opening and closing prices.

## TODO: exchange

## TODO: execution

## TODO: portcon

## TODO: risk_model

## TODO: signals

## TODO: simulation

## TODO: statistics

## TODO: system

## TODO: trading

## TODO: utils