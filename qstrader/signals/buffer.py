from collections import deque


class AssetPriceBuffers(object):
    """
    Utility class to store double-ended queue ("deque") based price buffers for usage in lookback-based indicator
    calculations.

    The input argument 'lookbacks' for constructor is a list of integers, where each integer represents the number of
    lookback periods to store prices for. This is necessary for signals that require multiple lookback periods, such as
    momentum signals that may require 1-month, 3-month, and 6-month lookbacks.

    The class creates a dictionary of price buffers for each asset-lookback pair with the corresponding deque having the
    length of the lookback periods.

    When a new price is appended for an asset, it is added to all of the corresponding lookback buffers for that asset.
    """

    @staticmethod
    def _asset_lookback_key(asset: str, lookback: int) -> str:
        """
        Create the buffer dictionary lookup key by pasting together the asset name and lookback period. This is
        necessary to create a unique key for each asset-lookback pair.

        Parameters
        ----------
        asset : `str`
            The asset symbol name.
        lookback : `int`
            The lookback period.

        Returns
        -------
        `str`
            The lookup key.
        """
        return '%s_%s' % (asset, lookback)

    def __init__(self, assets: list[str], lookbacks: list[int]=[12]):
        """
        Parameters
        ----------
        assets : `list[str]`
            The list of assets to create price buffers for.
        lookbacks : `list[int]`, optional
            The number of lookback periods to store prices for.
        """
        self.assets = assets
        self.lookbacks = lookbacks
        self.prices = self._create_all_assets_prices_buffer_dict()

    def _create_single_asset_prices_buffer_dict(self, asset: str) -> dict[str, deque[float]]:
        """
        Creates a dictionary of asset-lookback pair price buffers for a single asset. The size of each deque is
        determined by the lookback period, which is retrieved from the `self.lookbacks` list. The key for each deque is
        a string that combines the asset name and the lookback period.

        Returned result is like {'EQ:AAPL_12': deque(maxlen=12), 'EQ:AAPL_24': deque(maxlen=24)}. when asset is 'EQ:AAPL'
        and self.lookbacks are [12, 24].

        Returns
        -------
        `dict{str: deque[float]}`
            The price buffer dictionary.
        """
        return {
            AssetPriceBuffers._asset_lookback_key(asset, lookback): deque(maxlen=lookback)
            for lookback in self.lookbacks
        }

    def _create_all_assets_prices_buffer_dict(self) -> dict[str, deque[float]]:
        """
        Creates a dictionary of asset-lookback pair price buffers for all assets by calling the
        `_create_single_asset_prices_buffer_dict` method for each asset in the `self.assets` list.

        Returns
        -------
        `dict{str: deque[float]}`
            The price buffer dictionary.
        """
        prices = {}
        for asset in self.assets:
            prices.update(self._create_single_asset_prices_buffer_dict(asset))
        return prices

    def add_asset(self, asset: str) -> None:
        """
        Add an asset to the list of current assets. This is necessary if the asset is part of a DynamicUniverse and
        isn't present at the beginning of a backtest.

        Parameters
        ----------
        asset : `str`
            The asset symbol name.
        """
        if asset in self.assets:
            raise ValueError('Unable to add asset "%s" since it already exists in this price buffer.' % asset)
        else:
            self.prices.update(self._create_single_asset_prices_buffer_dict(asset))

    def append(self, asset: str, price: float) -> None:
        """
        Append a new price onto the price deque for the specific asset provided.

        Parameters
        ----------
        asset : `str`
            The asset symbol name.
        price : `float`
            The new price of the asset.
        """
        if price <= 0.0:
            raise ValueError('Unable to append non-positive price of "%0.2f" to metrics buffer for Asset "%s".' % (price, asset))

        # The asset may have been added to the universe subsequent to the beginning of the backtest and as such needs a
        # newly created pricing buffer
        asset_lookback_key = AssetPriceBuffers._asset_lookback_key(asset, self.lookbacks[0])
        if asset_lookback_key not in self.prices:
            self.prices.update(self._create_single_asset_prices_buffer_dict(asset))

        for lookback in self.lookbacks:
            self.prices[AssetPriceBuffers._asset_lookback_key(asset, lookback)].append(price)

    def remove_asset(self, asset: str) -> None:
        """
        Remove an asset from the list of current assets. This is necessary if the asset is part of a DynamicUniverse and
        is no longer present in the universe.

        Parameters
        ----------
        asset : `str`
            The asset symbol name.
        """
        if asset not in self.assets:
            raise ValueError('Unable to remove asset "%s" since it does not exist in this price buffer.' % asset)
        else:
            for lookback in self.lookbacks:
                del self.prices[AssetPriceBuffers._asset_lookback_key(asset, lookback)]
