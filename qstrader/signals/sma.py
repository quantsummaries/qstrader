import numpy as np
import pandas as pd

from qstrader.signals.signal import Signal
from qstrader.asset.universe.universe import Universe


class SMASignal(Signal):
    """
    Indicator class to calculate simple moving average
    of last N periods for a set of prices.

    Parameters
    ----------
    start_dt : `pd.Timestamp`
        The starting datetime (UTC) of the signal.
    universe : `Universe`
        The universe of assets to calculate the signals for.
    lookbacks : `list[int]`
        The number of lookback periods to store prices for.
    """

    def __init__(self, start_dt: pd.Timestamp, universe: Universe, lookbacks: list[int]):
        super().__init__(start_dt, universe, lookbacks)

    def _simple_moving_average(self, asset: str, lookback: int) -> float:
        """
        Calculate the 'trend' for the provided lookback
        period based on the simple moving average of the
        price buffers for a particular asset.

        Parameters
        ----------
        asset : `str`
            The asset symbol name.
        lookback : `int`
            The lookback period.

        Returns
        -------
        `float`
            The SMA value ('trend') for the period.
        """
        return np.mean(self.buffers.prices['%s_%s' % (asset, lookback)])

    def __call__(self, asset: str, lookback: int) -> float:
        """
        Calculate the lookback-period trend
        for the asset.

        Parameters
        ----------
        asset : `str`
            The asset symbol name.
        lookback : `int`
            The lookback period.

        Returns
        -------
        `float`
            The trend (SMA) for the period.
        """
        return self._simple_moving_average(asset, lookback)
