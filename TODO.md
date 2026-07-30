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

## broker

- [x] broker.py::Broker, abstract class that defines the interface for a broker.
  - simulated_broker.py::SimulatedBroker, subclass of Broker that simulates a broker for backtesting purposes.
- [x] fee_model.py::FeeModel, abstract class that defines the interface for a fee model.
  - fixed_fee_model.py::FixedFeeModel, subclass of FeeModel that applies a fixed fee per trade.
  - percentage_fee_model.py::PercentageFeeModel, subclass of FeeModel that applies a percentage fee per trade.
- [x] transaction.py::Transaction, class that defines the interface for a transaction.
- [x] portfolio.py::Portfolio, class that defines the interface for a portfolio.
- [x] portfolio_event.py::PortfolioEvent, class that defines the interface for a portfolio event.
- [x] position.py::Position, class that defines the interface for a position.
- [x] position_handler.py::PositionHandler, class that defines the interface for a position handler.

## data

- [x] backtest_data_handler.py::BacktestDataHandler, provides an asset's latest bid, ask, and mid prices, as well as the historical range close prices. 
- [x] daily_bar_csv.py::CSVDailyBarDataSource, encapsulates loading, preparation and querying of CSV files of daily 'bar' OHLCV data. The CSV files are converted into a intraday
    timestamped Pandas DataFrame with opening and closing prices.

## exchange

- [x] exchange.py::Exchange, abstract class that defines the interface for an exchange.
  - simulated_exchange.py::SimulatedExchange, subclass of Exchange that simulates an exchange for backtesting purposes.

## execution

- [x] order.py::Order, class that defines the interface for an order.
- [x] execution_handler.py::ExecutionHandler, class that defines the interface for an execution handler.
- [x] execution_algo.py::ExecutionAlgorithm, class that defines the interface for an execution algorithm.
  - market_order.py::MarketOrderExecutionAlgorithm, subclass of ExecutionAlgorithm that represents a market order.
  
## TODO: portcon

## risk_model

- [x] risk_model.py::RiskModel, abstract class that defines the interface for a risk model.
  
## signals

- [x] buffer.py::AssetPriceBuffers, class that defines the interface for an asset price buffer.
- [x] signal.py::Signal, class that defines the interface for a signal.
  - momentum.py::MomentumSignal, subclass of Signal that calculates the price momentum of an asset.
  - sma.py::SMASignal, subclass of Signal that calculates the price mean reversion of an asset.
  - vol.py::VolatilitySignal, subclass of Signal that calculates the price volatility of an asset.
- [x] signals_collection.py::SignalsCollection, class that defines the interface for a collection of signals.

## simulation

- [x] event.py::SimulationEvent, class that defines the interface for a simulation event.
- [x] sim_engine.py::SimulationEngine, class that defines the interface for a simulation engine.
  - daily_bday.py::DailyBusinessDaySimulationEngine, subclass of SimulationEngine that simulates a daily business day simulation engine.

## statistics

- [x] json_statistics.py::JSONStatistics, class that defines the interface for a statistics object that can be serialized to JSON.
- [x] performance.py
  - aggregate_returns(...), function that aggregates returns into a single return value.
  - create_cagr(...), function that calculates the compound annual growth rate (CAGR) of a return series.
  - create_sharpe_ratio(...), function that calculates the Sharpe ratio of a return series.
  - create_sortino_ratio(...), function that calculates the Sortino ratio of a return series.
  - calculate_drawdowns(...), function that calculates the drawdowns of a return series.
- [x] statistics.py::Statistics, class that defines the interface for a statistics object that can be serialized to JSON and generates a Matplotlib 'one-pager' strategy performance report.
  - tearsheet.py::TearsheetStatistics, subclass of Statistics that generates a Matplotlib 'one-pager' strategy performance report.

## TODO: system

## TODO: trading

## utils

- [x] utils.py::string_colour(...), function that returns a string with ANSI colour codes for terminal output.