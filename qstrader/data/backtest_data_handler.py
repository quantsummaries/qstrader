import numpy as np
import pandas as pd

from qstrader.asset.universe.universe import Universe
from qstrader.data.daily_bar_csv import CSVDailyBarDataSource

class BacktestDataHandler(object):
    """
    Encapsulates loading, preparing, and querying daily OHLCV CSV files. Its core idea is that daily bars are not
    consumed directly. Instead, each bar is transformed into a small price timeline with two entries per trading day:
    one at the assumed market open, one at the assumed market close. This allows other parts of the system to query
    “latest bid/ask” at a timestamp during a daily backtest.
    """

    def __init__(
        self,
        universe: Universe,
        data_sources: list[CSVDailyBarDataSource]
    ):
        """
        Args:
            universe (Universe): the universe to query data for.
            data_sources (list[CSVDailyBarDataSource]): the data sources to query data from.
        """
        self.universe = universe
        self.data_sources = data_sources

    def get_asset_latest_bid_price(self, dt: pd.Timestamp, asset_symbol: str) -> float:
        """ Get the bid price of an asset at a given timestamp.
        Args:
            dt (pd.Timestamp): the timestamp to query the latest bid price for.
            asset_symbol (str): the asset symbol to query the latest bid price for.

        Returns:
            float: the latest bid price.
        """
        if asset_symbol not in self.universe.get_assets(dt):
            raise ValueError(f"Asset {asset_symbol} not in universe at {dt}.")

        bid = np.nan
        for ds in self.data_sources:
            try:
                bid = ds.get_bid(dt, asset_symbol)
                if not np.isnan(bid):
                    return bid
            except Exception:
                bid = np.nan
        return bid

    def get_asset_latest_ask_price(self, dt: pd.Timestamp, asset_symbol: str) -> float:
        """ Get the ask price of an asset at a given timestamp.
        Args:
            dt (pd.Timestamp): the timestamp to query the latest ask price for.
            asset_symbol (str): the asset symbol to query the latest ask price for.
        """
        if asset_symbol not in self.universe.get_assets(dt):
            raise ValueError(f"Asset {asset_symbol} not in universe at {dt}.")

        ask = np.nan
        for ds in self.data_sources:
            try:
                ask = ds.get_ask(dt, asset_symbol)
                if not np.isnan(ask):
                    return ask
            except Exception:
                ask = np.nan
        return ask

    def get_asset_latest_bid_ask_price(self, dt: pd.Timestamp, asset_symbol: str) -> tuple[float, float]:
        """
        Get the bid and ask price of an asset at a given timestamp.
        Args:
            dt (pd.Timestamp): the timestamp to query the latest bid and ask price for.
            asset_symbol (str): the asset symbol to query the latest bid and ask price for.

        Returns:
            tuple[float, float]: the latest bid and ask price.
        """
        bid = self.get_asset_latest_bid_price(dt, asset_symbol)
        ask = self.get_asset_latest_ask_price(dt, asset_symbol)
        return bid, ask

    def get_asset_latest_mid_price(self, dt: pd.Timestamp, asset_symbol: str) -> float:
        """
        Get the mid price of an asset at a given timestamp.
        Args:
            dt (pd.Timestamp): the timestamp to query the latest mid price for.
            asset_symbol (str): the asset symbol to query the latest mid price for.

        Returns:
            float: the latest mid price.
        """
        bid_ask = self.get_asset_latest_bid_ask_price(dt, asset_symbol)
        try:
            mid = (bid_ask[0] + bid_ask[1]) / 2.0
        except Exception:
            # TODO: Log this
            mid = np.nan
        return mid

    def get_assets_historical_range_close_price(
        self, start_dt: pd.Timestamp, end_dt: pd.Timestamp, asset_symbols: list[str]) -> pd.DataFrame:
        """
        Get the historical range of closing prices for multiple assets.
        Args:
            start_dt (pd.Timestamp): the starting timestamp of the range.
            end_dt (pd.Timestamp): the ending timestamp of the range.
            asset_symbols (list[str]): the list of asset symbols to query.

        Returns:
            pd.DataFrame: the historical range of closing prices for each asset.
        """
        prices_df = None
        for ds in self.data_sources:
            try:
                prices_df = ds.get_assets_historical_closes(
                    start_dt, end_dt, asset_symbols
                )
                if prices_df is not None:
                    return prices_df
            except Exception:
                raise
        return prices_df
