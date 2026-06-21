import pytest

from qstrader.asset.equity import Equity


@pytest.mark.parametrize(
    'name,symbol,tax_exempt,expected',
    [
        ('SPDR S&P 500 ETF', 'SPY', True, ['SPDR S&P 500 ETF', 'SPY', True]),
        ('iShares Core U.S. Aggregate Bond ETF', 'AGG', False, ['iShares Core U.S. Aggregate Bond ETF', 'AGG', False]),
    ]
)
def test_equity(name: str, symbol: str, tax_exempt: bool, expected: list):
    """
    Tests that the Equity asset is correctly instantiated.
    """
    equity = Equity(name=name, symbol=symbol, tax_exempt=tax_exempt)

    assert not equity.cash_like
    assert equity.name == expected[0]
    assert equity.symbol == expected[1]
    assert equity.tax_exempt == expected[2]
