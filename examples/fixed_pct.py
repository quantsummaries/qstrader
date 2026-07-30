#!/usr/bin/python

# script to backtest a portfolio with fixed percentage of compositions.

import argparse
import os
from datetime import datetime

import pandas as pd
import pytz

from qstrader.alpha_model.fixed_signals import FixedSignalsAlphaModel
from qstrader.asset.equity import Equity
from qstrader.asset.universe.static import StaticUniverse
from qstrader.constants import DATA_DIR
from qstrader.data.backtest_data_handler import BacktestDataHandler
from qstrader.data.daily_bar_csv import CSVDailyBarDataSource
from qstrader.statistics.tearsheet import TearsheetStatistics
from qstrader.trading.backtest import BacktestTradingSession

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-sd', '--start_dt', type=int, required=True, help='Start date of format YYYYMMDD')
    parser.add_argument('-ed', '--end_dt', type=int, required=True, help='End date of format YYYYMMDD')
    parser.add_argument('-s', '--strategy_symbols', type=str, required=True, help='Comma-separated strategy symbols')
    parser.add_argument('-a', '--strategy_allocations', type=str, required=True, help='Comma-separated strategy allocations (in decimals)')
    parser.add_argument('-b', '--benchmark', type=str, required=True, help='Benchmark asset')
    parser.add_argument('-f', '--rebalance_frequency', type=str, required=False,
                        help='Rebalance frequency, "daily", "weekly", "end_of_month", and "buy_and_hold"; (default: end_of_month)',
                        default='end_of_month')

    return parser.parse_args()



if __name__ == "__main__":
    # example: uv run ./examples/fixed_pct.py -sd 20220308 -ed 20260729 -s SPY,CTA,GLD -a 0.33,0.34,0.33 -f end_of_month -b SPY

    args = parse_args()

    start_dt = pd.Timestamp(f'{datetime.strptime(str(args.start_dt), "%Y%m%d").strftime("%Y-%m-%d")} 14:30:00',
                            tz=pytz.UTC)
    end_dt = pd.Timestamp(f'{datetime.strptime(str(args.end_dt), "%Y%m%d").strftime("%Y-%m-%d")} 23:59:00',
                          tz=pytz.UTC)
    strategy_symbols = args.strategy_symbols.split(',')
    strategy_allocations = [float(x) for x in args.strategy_allocations.split(',')]
    if len(strategy_allocations) != len(strategy_symbols):
        raise ValueError('Length of strategy allocations should be equal to length of strategy symbols')
    freq = args.rebalance_frequency
    benchmark = args.benchmark

    # Construct the symbols and assets necessary for the backtest
    strategy_assets = ['EQ:%s' % symbol for symbol in strategy_symbols]
    strategy_universe = StaticUniverse(strategy_assets)

    # To avoid loading all CSV files in the directory, set the data source to load only those provided symbols
    csv_dir = os.environ.get('QSTRADER_CSV_DATA_DIR', DATA_DIR)
    data_source = CSVDailyBarDataSource(str(csv_dir), 'Equity', csv_symbols=strategy_symbols)
    data_handler = BacktestDataHandler(strategy_universe, data_sources=[data_source])

    # Construct an Alpha Model that simply provides static allocations to a universe of assets
    # In this case 33% SPY ETF, 33% GLD ETF, 33% CTA ETF, rebalanced at the end of each month
    strategy_alpha_model = FixedSignalsAlphaModel(dict(zip(strategy_assets, strategy_allocations)))
    strategy_backtest = BacktestTradingSession(
        start_dt,
        end_dt,
        strategy_universe,
        strategy_alpha_model,
        rebalance=freq,
        long_only=True,
        cash_buffer_percentage=0.01,
        data_handler=data_handler
    )
    strategy_backtest.run()

    # Construct benchmark assets (buy & hold SPY)
    benchmark_assets = [f'EQ:{benchmark}']

    benchmark_universe = StaticUniverse(benchmark_assets)

    # Construct a benchmark Alpha Model that provides
    # 100% static allocation to the SPY ETF, with no rebalance
    benchmark_alpha_model = FixedSignalsAlphaModel({f'EQ:{benchmark}': 1.0})
    benchmark_backtest = BacktestTradingSession(
        start_dt,
        end_dt,
        benchmark_universe,
        benchmark_alpha_model,
        rebalance='buy_and_hold',
        long_only=True,
        cash_buffer_percentage=0.01,
        data_handler=data_handler
    )
    benchmark_backtest.run()

    # Performance Output
    tearsheet = TearsheetStatistics(
        strategy_equity=strategy_backtest.get_equity_curve(),
        benchmark_equity=benchmark_backtest.get_equity_curve(),
        title=f'Fixed Percentage Strategy {dict(zip(strategy_symbols, strategy_allocations))} vs. {benchmark}'
    )
    tearsheet.plot_results()
