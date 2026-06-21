#!/usr/bin/env python

# script of qstrader to backtest a portfolio with fixed percentage of compositions.

import argparse
import os
from datetime import datetime

import pandas as pd
import pytz

from qstrader.alpha_model.fixed_signals import FixedSignalsAlphaModel
from qstrader.asset.universe.static import StaticUniverse
from qstrader.constants import DATA_DIR
from qstrader.data.backtest_data_handler import BacktestDataHandler
from qstrader.data.daily_bar_csv import CSVDailyBarDataSource
from qstrader.statistics.tearsheet import TearsheetStatistics
from qstrader.trading.backtest import BacktestTradingSession

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-sd', '--start_dt', type=str, metavar="", required=True, help='Start date of format YYYY-MM-DD')
    parser.add_argument('-ed', '--end_dt', type=str, metavar="", required=True, help='End date of format YYYY-MM-DD')
    parser.add_argument('-s', '--strategy_symbols', type=str, metavar="", required=True, help='Comma-separated strategy symbols')
    parser.add_argument('-sa', '--strategy_allocations', type=str, metavar="", required=True, help='Comma-separated strategy allocations (in decimals)')
    parser.add_argument('-b', '--benchmark_symbols', type=str, metavar="", required=True, help='Comma-separated benchmark assets')
    parser.add_argument('-ba', '--benchmark_allocations', type=str, metavar="", required=True, help='Comma-separated benchmark allocations (in decimals)')
    parser.add_argument('-dd', '--data_directory', type=str, metavar="", required=False, help='Data directory (default: DATA_DIR)', default=DATA_DIR)
    parser.add_argument('-sf', '--strategy_rebalance_frequency', type=str, metavar="", required=False, choices=['daily', 'weekly', 'end_of_month', 'buy_and_hold'],
                        help='Strategy Rebalance frequency (default: end_of_month)',
                        default='end_of_month')
    parser.add_argument('-bf', '--benchmark_rebalance_frequency', type=str, metavar="", required=False, choices=['daily', 'weekly', 'end_of_month', 'buy_and_hold'],
                        help='Benchmark Rebalance frequency (default: buy_and_hold)',
                        default='buy_and_hold')
    parser.add_argument('-t', '--title', type=str, metavar="", required=False, help='Title of the backtest (default: Fixed Percentage Strategy vs. Benchmark)', default='Fixed Percentage Strategy vs. Benchmark')

    return parser.parse_args()



if __name__ == "__main__":
    # example: uv run python qst_static_alloc.py -sd 20220308 -ed 20260729 -s VTI,CTA,GLD -sa 0.33,0.34,0.33 -f end_of_month -b SPY,AGG -ba 0.6,0.4 -dd ../data/

    args = parse_args()

    start_dt = pd.Timestamp(f'{datetime.strptime(str(args.start_dt), "%Y-%m-%d").strftime("%Y-%m-%d")} 14:30:00',
                            tz=pytz.UTC)
    end_dt = pd.Timestamp(f'{datetime.strptime(str(args.end_dt), "%Y-%m-%d").strftime("%Y-%m-%d")} 23:59:00',
                          tz=pytz.UTC)

    strategy_symbols = args.strategy_symbols.split(',')
    strategy_allocations = [float(x) for x in args.strategy_allocations.split(',')]
    if len(strategy_allocations) != len(strategy_symbols):
        raise ValueError('Length of strategy allocations should be equal to length of strategy symbols')

    data_dir = args.data_directory

    strat_freq = args.strategy_rebalance_frequency
    bench_freq = args.benchmark_rebalance_frequency

    benchmark_symbols = args.benchmark_symbols.split(',')
    benchmark_allocations = [float(x) for x in args.benchmark_allocations.split(',')]
    if len(benchmark_allocations) != len(benchmark_symbols):
        raise ValueError('Length of benchmark allocations should be equal to length of benchmark assets')

    # Construct the symbols and assets necessary for the backtest
    strategy_assets = ['EQ:%s' % symbol for symbol in strategy_symbols]
    strategy_universe = StaticUniverse(strategy_assets)

    # To avoid loading all CSV files in the directory, set the data source to load only those provided symbols
    csv_dir = data_dir
    data_source = CSVDailyBarDataSource(str(csv_dir), 'Equity', csv_symbols=strategy_symbols)
    data_handler = BacktestDataHandler(strategy_universe, data_sources=[data_source])

    # Construct an Alpha Model that simply provides static allocations to a universe of assets
    strategy_alpha_model = FixedSignalsAlphaModel(dict(zip(strategy_assets, strategy_allocations)))
    strategy_backtest = BacktestTradingSession(
        start_dt,
        end_dt,
        strategy_universe,
        strategy_alpha_model,
        rebalance=strat_freq,
        long_only=True,
        cash_buffer_percentage=0.01,
        data_handler=data_handler
    )
    strategy_backtest.run()

    # Construct benchmark assets (buy & hold SPY)
    benchmark_assets = ['EQ:%s' % symbol for symbol in benchmark_symbols]
    benchmark_universe = StaticUniverse(benchmark_assets)
    data_source = CSVDailyBarDataSource(str(csv_dir), 'Equity', csv_symbols=benchmark_symbols)
    data_handler = BacktestDataHandler(benchmark_universe, data_sources=[data_source])

    # Construct a benchmark Alpha Model
    benchmark_alpha_model = FixedSignalsAlphaModel(dict(zip(benchmark_assets, benchmark_allocations)))
    benchmark_backtest = BacktestTradingSession(
        start_dt,
        end_dt,
        benchmark_universe,
        benchmark_alpha_model,
        rebalance=bench_freq,
        long_only=True,
        cash_buffer_percentage=0.01,
        data_handler=data_handler
    )
    benchmark_backtest.run()

    # Performance Output
    tearsheet = TearsheetStatistics(
        strategy_equity=strategy_backtest.get_equity_curve(),
        benchmark_equity=benchmark_backtest.get_equity_curve(),
        title=args.title
    )
    tearsheet.plot_results()
