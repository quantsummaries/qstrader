import numpy as np
import pandas as pd
import pytest

from qstrader.statistics.performance import aggregate_returns, create_cagr


def test_aggregate_returns_weekly_keeps_iso_week_together_across_year_boundary():
    """
    Ensure weekly aggregation uses ISO year/week buckets so a single
    ISO week spanning a calendar year boundary is not split.
    """
    returns = pd.Series(
        [0.10, 0.10],
        index=pd.to_datetime(['2020-12-31', '2021-01-01'])
    )

    aggregated = aggregate_returns(returns, 'weekly')

    assert len(aggregated) == 1
    assert np.isclose(aggregated.iloc[0], 0.21)
    assert tuple(aggregated.index[0]) == (2020, 53)


def test_aggregate_returns_monthly_handles_total_loss_without_warning_value_change():
    """
    A -100% daily return should aggregate cleanly to -100% for the period.
    """
    returns = pd.Series(
        [0.10, -1.0],
        index=pd.to_datetime(['2024-01-01', '2024-01-02'])
    )

    aggregated = aggregate_returns(returns, 'monthly')

    assert len(aggregated) == 1
    assert aggregated.index[0] == (2024, 1)
    assert aggregated.iloc[0] == -1.0


def test_aggregate_returns_monthly_ignores_nan_values_in_group():
    """
    Missing returns in a period should not poison the entire aggregate.
    """
    returns = pd.Series(
        [0.10, np.nan],
        index=pd.to_datetime(['2024-01-01', '2024-01-02'])
    )

    aggregated = aggregate_returns(returns, 'monthly')

    assert len(aggregated) == 1
    assert aggregated.index[0] == (2024, 1)
    assert np.isclose(aggregated.iloc[0], 0.10)


@pytest.mark.parametrize('convert_to', ['weekly', 'monthly', 'yearly'])
def test_aggregate_returns_rejects_non_datetime_index(convert_to):
    """
    The function expects a DatetimeIndex-backed returns series.
    """
    returns = pd.Series([0.01, 0.02], index=[0, 1])

    with pytest.raises(TypeError, match='DatetimeIndex'):
        aggregate_returns(returns, convert_to)


def test_aggregate_returns_rejects_invalid_frequency():
    """
    Unsupported aggregation frequencies should raise a clear error.
    """
    returns = pd.Series([0.01], index=pd.to_datetime(['2024-01-01']))

    with pytest.raises(ValueError, match='weekly, monthly or yearly'):
        aggregate_returns(returns, 'daily')


@pytest.mark.parametrize(
    'curve,expected',
    [
        (
            pd.Series([1.0, 1.10]),
            0.10,
        ),
        (
            pd.Series([100.0, 110.0]),
            0.10,
        ),
    ]
)
def test_create_cagr_handles_normalized_and_dollar_denominated_curves(curve, expected):
    """
    CAGR should be identical for equivalent normalized and dollar-denominated
    equity curves.
    """
    assert np.isclose(create_cagr(curve, periods=2), expected)


@pytest.mark.parametrize(
    'curve,match',
    [
        (pd.Series([], dtype=float), 'at least one non-NaN value'),
        (pd.Series([0.0, 1.0]), 'start with a positive value'),
        (pd.Series([np.nan, np.nan]), 'at least one non-NaN value'),
    ]
)
def test_create_cagr_rejects_invalid_curves(curve, match):
    """
    Invalid equity curves should fail fast with a clear error.
    """
    with pytest.raises(ValueError, match=match):
        create_cagr(curve)


