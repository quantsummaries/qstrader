from abc import ABC, abstractmethod

import pandas as pd

class Universe(ABC):
    """
    Interface specification for an Asset Universe.
    """

    @abstractmethod
    def get_assets(self, dt: pd.Timestamp) -> list[str]:
        raise NotImplementedError(
            "Should implement get_assets()"
        )
