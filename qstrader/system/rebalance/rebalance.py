from abc import ABC, abstractmethod


class Rebalance(ABC):
    """
    Interface to a generic list of system logic and
    trade order rebalance timestamps.
    """

    @abstractmethod
    def output_rebalances(self):
        raise NotImplementedError(
            "Should implement output_rebalances()"
        )
