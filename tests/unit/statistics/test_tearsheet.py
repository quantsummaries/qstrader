import numpy as np
import pandas as pd
import pytest

from qstrader.statistics.tearsheet import TearsheetStatistics


@pytest.mark.parametrize(
    'returns,expected',
    [
        (
            pd.Series([0.01, 0.02, -0.01, -0.02, 0.0, 0.03]),
            np.array([0.03, -0.03, 0.03]),
        ),
        (
            pd.Series([0.0, 0.0, 0.0]),
            np.array([]),
        ),
        (
            pd.Series([np.nan, 0.01, 0.02, 0.0, -0.01]),
            np.array([0.03, -0.01]),
        ),
    ]
)
def test_calculate_trade_returns_groups_non_zero_sign_runs(returns, expected):
    """
    Trade returns are defined as sums of consecutive non-zero returns
    that share the same sign. Zeros and sign changes delimit trades.
    """
    actual = TearsheetStatistics._calculate_trade_returns(returns)
    assert np.allclose(actual, expected)

