from qstrader.asset.universe.universe import Universe
import pandas as pd

class StaticUniverse(Universe):
    """
    An Asset Universe that does not change its composition
    through time.

    Parameters
    ----------
    asset_list : `list[str]`
        The list of Asset symbols that form the StaticUniverse.
    """

    def __init__(self, asset_list: list[str]):
        self.asset_list = asset_list

    def get_assets(self, dt: pd.Timestamp) -> list[str]:
        """
        Obtain the list of assets in the Universe at a particular
        point in time. This will always return a static list
        independent of the timestamp provided.

        Parameters
        ----------
        dt : `pd.Timestamp`
            The timestamp at which to retrieve the Asset list.

        Returns
        -------
        `list[str]`
            The list of Asset symbols in the static Universe.
        """
        return self.asset_list
