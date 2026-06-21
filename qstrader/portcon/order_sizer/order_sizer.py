from abc import ABC, abstractmethod

import pandas as pd


class OrderSizer(ABC):
    """
    Creates a target portfolio of quantities for each Asset
    using its provided weight and total equity available in the Broker portfolio.
    """

    @abstractmethod
    def __call__(self, dt: pd.Timestamp, weights: dict[str, float]) -> dict[str, dict]:
        raise NotImplementedError(
            "Should implement call()"
        )
