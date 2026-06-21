from abc import ABC, abstractmethod

import pandas as pd

from qstrader.execution.order import Order


class ExecutionAlgorithm(ABC):
    """
    Callable which takes in a list of desired rebalance Orders
    and outputs a new Order list with a particular execution
    algorithm strategy.
    """

    @abstractmethod
    def __call__(self, dt: pd.Timestamp, initial_orders: list[Order]) -> list[Order]:
        raise NotImplementedError(
            "Should implement __call__()"
        )
