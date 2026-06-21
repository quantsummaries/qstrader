from __future__ import annotations

from abc import ABC, abstractmethod

from qstrader.broker.broker import Broker


class FeeModel(ABC):
    """
    Abstract class to handle the calculation of brokerage
    commission, fees and taxes.
    """

    @abstractmethod
    def _calc_commission(self, asset: str, quantity: int, consideration: float, broker: Broker|None):
        raise NotImplementedError(
            "Should implement _calc_commission()"
        )

    @abstractmethod
    def _calc_tax(self, asset: str, quantity: int, consideration: float, broker: Broker|None=None):
        raise NotImplementedError(
            "Should implement _calc_tax()"
        )

    @abstractmethod
    def calc_total_cost(self, asset: str, quantity: int, consideration: float, broker: Broker|None=None):
        raise NotImplementedError(
            "Should implement calc_total_cost()"
        )
