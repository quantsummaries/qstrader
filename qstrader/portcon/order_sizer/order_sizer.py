from abc import ABCMeta, abstractmethod

import pandas as pd


class OrderSizer(object):
    """
    Creates a target portfolio of quantities for each Asset
    using its provided weight and total equity available in the Broker portfolio.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def __call__(self, dt: pd.Timestamp, weights: dict[str, float]) -> dict[str, dict]:
        raise NotImplementedError(
            "Should implement call()"
        )
