from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class PortfolioOptimiser(ABC):
    """
    Abstract interface for a PortfolioOptimiser callable.

    A derived-class instance of PortfolioOptimisertakes in
    a list of Assets (not an Asset Universe) and an optional
    DataHandler instance in order to generate target weights
    for Assets.

    These are then potentially modified by the PortfolioConstructionModel,
    which generates a list of rebalance Orders.

    Implementing __call__ produces a dictionary keyed by
    Asset and with a scalar value as the weight.
    """

    @abstractmethod
    def __call__(self, dt: pd.Timestamp, initial_weights: dict[str, float]) -> dict:
        raise NotImplementedError(
            "Should implement __call__()"
        )
