from abc import ABCMeta, abstractmethod

import pandas as pd

class Universe(object):
    """
    Interface specification for an Asset Universe.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_assets(self, dt: pd.Timestamp) -> list[str]:
        raise NotImplementedError(
            "Should implement get_assets()"
        )
