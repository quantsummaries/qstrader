import os
import pytz

import pandas as pd

from qstrader.constants import DATA_DIR
from qstrader.alpha_model.top_n_momentum import TopNMomentumAlphaModel
from qstrader.asset.universe.dynamic import DynamicUniverse
from qstrader.data.backtest_data_handler import BacktestDataHandler
from qstrader.data.daily_bar_csv import CSVDailyBarDataSource
from qstrader.signals.signals_collection import SignalsCollection
from qstrader.signals.momentum import MomentumSignal


if __name__ == '__main__':
    # Duration of the backtest
    start_dt = pd.Timestamp('1998-12-22 14:30:00', tz=pytz.UTC)
    burn_in_dt = pd.Timestamp('1999-12-22 14:30:00', tz=pytz.UTC)
    end_dt = pd.Timestamp('2020-12-31 23:59:00', tz=pytz.UTC)

    # Model parameters
    mom_lookback = 126  # Six months worth of business days
    mom_top_n = 3  # Number of assets to include at any one time

    # Construct the symbols and assets necessary for the backtest
    # This utilises the SPDR US sector ETFs, all beginning with XL
    strategy_symbols = ['XL%s' % sector for sector in "BCEFIKPUVY"]
    assets = ['EQ:%s' % symbol for symbol in strategy_symbols]

    # As this is a dynamic universe of assets (XLC is added later)
    # we need to tell QSTrader when XLC can be included. This is
    # achieved using an asset dates dictionary
    asset_dates = {asset: start_dt for asset in assets}
    asset_dates['EQ:XLC'] = pd.Timestamp('2018-06-18 00:00:00', tz=pytz.UTC)
    strategy_universe = DynamicUniverse(asset_dates)

    # To avoid loading all CSV files in the directory, set the
    # data source to load only those provided symbols
    csv_dir = os.environ.get('QSTRADER_CSV_DATA_DIR', DATA_DIR)
    strategy_data_source = CSVDailyBarDataSource(str(csv_dir), 'Equity', csv_symbols=strategy_symbols)
    strategy_data_handler = BacktestDataHandler(strategy_universe, data_sources=[strategy_data_source])

    # Generate the signals (in this case holding-period return based
    # momentum) used in the top-N momentum alpha model
    momentum = MomentumSignal(start_dt, strategy_universe, lookbacks=[mom_lookback])
    signals = SignalsCollection({'momentum': momentum}, strategy_data_handler)

    # Generate the alpha model instance for the top-N momentum alpha model
    strategy_alpha_model = TopNMomentumAlphaModel(
        signals, mom_lookback, mom_top_n, strategy_universe, strategy_data_handler
    )