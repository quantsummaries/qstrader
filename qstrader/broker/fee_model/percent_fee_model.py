from __future__ import annotations

from qstrader.broker.broker import Broker
from qstrader.broker.fee_model.fee_model import FeeModel


class PercentFeeModel(FeeModel):
    """
    A FeeModel subclass that produces a percentage cost
    for tax and commission.

    Parameters
    ----------
    commission_pct : `float`, optional
        The percentage commission applied to the consideration.
        0-100% is in the range [0.0, 1.0]. Hence, e.g. 0.1% is 0.001
    tax_pct : `float`, optional
        The percentage tax applied to the consideration.
        0-100% is in the range [0.0, 1.0]. Hence, e.g. 0.1% is 0.001
    """

    def __init__(self, commission_pct: float=0.0, tax_pct: float=0.0):
        super().__init__()
        self.commission_pct = commission_pct
        self.tax_pct = tax_pct

    def _calc_commission(self, asset: str, quantity: int, consideration: float, broker: Broker|None=None) -> float:
        """
        Returns the percentage commission from the consideration.

        Parameters
        ----------
        asset : `str`
            The asset symbol string.
        quantity : `int`
            The quantity of assets (needed for InteractiveBrokers
            style calculations).
        consideration : `float`
            Price times quantity of the order.
        broker : `Broker`, optional
            An optional Broker reference.

        Returns
        -------
        `float`
            The percentage commission.
        """
        return self.commission_pct * abs(consideration)

    def _calc_tax(self, asset, quantity, consideration, broker: Broker|None=None) -> float:
        """
        Returns the percentage tax from the consideration.

        Parameters
        ----------
        asset : `str`
            The asset symbol string.
        quantity : `int`
            The quantity of assets (needed for InteractiveBrokers
            style calculations).
        consideration : `float`
            Price times quantity of the order.
        broker : `Broker`, optional
            An optional Broker reference.

        Returns
        -------
        `float`
            The percentage tax.
        """
        return self.tax_pct * abs(consideration)

    def calc_total_cost(self, asset: str, quantity: int, consideration: float, broker: Broker|None=None) -> float:
        """
        Calculate the total of any commission and/or tax
        for the trade of size 'consideration'.

        Parameters
        ----------
        asset : `str`
            The asset symbol string.
        quantity : `int`
            The quantity of assets (needed for InteractiveBrokers
            style calculations).
        consideration : `float`
            Price times quantity of the order.
        broker : `Broker`, optional
            An optional Broker reference.

        Returns
        -------
        `float`
            The total commission and tax.
        """
        commission = self._calc_commission(asset, quantity, consideration, broker)
        tax = self._calc_tax(asset, quantity, consideration, broker)
        return commission + tax
