import pandas as pd

from qstrader.statistics.json_statistics import JSONStatistics


def test_timestamp_serialization_is_timezone_safe_for_utc_equity_curves():
    """
    UTC-aware equity curves should serialize to stable epoch milliseconds.
    """
    equity_curve = pd.DataFrame(
        {
            'Equity': [100.0, 90.0, 72.0],
        },
        index=pd.to_datetime([
            '2024-01-01 00:00:00+00:00',
            '2024-01-02 00:00:00+00:00',
            '2024-01-03 00:00:00+00:00',
        ])
    )

    target_allocations = pd.DataFrame(
        {
            'EQ:SPY': [0.5, 0.6, 0.7],
        },
        index=equity_curve.index
    )

    stats = JSONStatistics(equity_curve, target_allocations, output_filename='unused.json')
    strategy = stats.statistics['strategy']

    expected_epoch_ms = [1704067200000, 1704153600000, 1704240000000]

    assert [row[0] for row in strategy['equity_curve']] == expected_epoch_ms
    assert [row[0] for row in strategy['returns']] == expected_epoch_ms
    assert [row[0] for row in strategy['cum_returns']] == expected_epoch_ms
    assert [row[0] for row in strategy['drawdowns']] == expected_epoch_ms
    assert [row[0] for row in strategy['target_allocations'][0]['data']] == expected_epoch_ms
    assert [row[0] for row in strategy['target_allocations'][0]['data']] == expected_epoch_ms

