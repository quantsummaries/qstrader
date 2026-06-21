from abc import ABC, abstractmethod
import pandas as pd


class AlphaModel(ABC):
    """
    Abstract interface for an AlphaModel callable.

    A derived-class instance of AlphaModel takes in an Asset
    Universe and an optional DataHandler instance in order
    to generate forecast signals on Assets.

    The class constructor also takes in a SignalsCollection instance,
    which is used to generate signals for the Assets in the Universe.

    These signals are used by the PortfolioConstructionModel
    to generate target weights for the portfolio.

    Implementing __call__ produces a dictionary keyed by
    Asset and with a scalar value as the signal.
    """

    @abstractmethod
    def __call__(self, dt: pd.Timestamp) -> dict[str, float]:
        """
        Calculates the signal values for the alpha model.

        Parameters
        ----------
        dt : `pd.Timestamp`
            The datetime for which the signal values should be calculated.

        Returns
        -------
        `dict{str: float}`
            The newly created signal values dictionary.
        """
        raise NotImplementedError(
            "Should implement __call__()"
        )
