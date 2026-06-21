from abc import ABC, abstractmethod

import pandas as pd


class Exchange(ABC):
    """
    Interface to a trading exchange such as the NYSE or LSE.
    This class family is only required for simulations, rather than
    live or paper trading.

    It exposes methods for obtaining calendar capability
    for trading opening times and market events.
    """

    @abstractmethod
    def is_open_at_datetime(self, dt: pd.Timestamp) -> bool:
        raise NotImplementedError(
            "Should implement is_open_at_datetime()"
        )
