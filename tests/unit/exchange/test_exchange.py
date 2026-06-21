import pandas as pd
import pytest

from qstrader.exchange.exchange import Exchange
from qstrader.exchange.simulated_exchange import SimulatedExchange


UTC_START_DT = pd.Timestamp('2024-01-01 00:00:00', tz='UTC')


class IncompleteExchange(Exchange):
    pass


def test_exchange_cannot_be_instantiated_without_is_open_implementation():
    """
    Exchange is an abstract base class and must not be instantiated
    without implementing is_open_at_datetime.
    """
    with pytest.raises(TypeError):  # type: ignore[abstract]
        IncompleteExchange()


@pytest.mark.parametrize(
    'start_dt,name,expected_open,expected_close',
    [
        (
            UTC_START_DT,
            'NYSE',
            (14, 30),
            (21, 0)
        )
    ]
)
def test_simulated_exchange_initialises_supported_exchange(
    start_dt, name, expected_open, expected_close
):
    """
    SimulatedExchange should store the constructor parameters and set
    NYSE market hours in UTC.
    """
    exchange = SimulatedExchange(start_dt, name=name)

    assert exchange.start_dt == start_dt
    assert exchange.name == name
    assert exchange.open_dt.hour == expected_open[0]
    assert exchange.open_dt.minute == expected_open[1]
    assert exchange.close_dt.hour == expected_close[0]
    assert exchange.close_dt.minute == expected_close[1]


@pytest.mark.parametrize('name', ['LSE', 'NASDAQ', ''])
def test_simulated_exchange_rejects_unsupported_exchange_names(name):
    """
    Only NYSE is currently supported by SimulatedExchange.
    """
    with pytest.raises(ValueError, match='not supported'):
        SimulatedExchange(UTC_START_DT, name=name)


@pytest.mark.parametrize(
    'dt,expected',
    [
        (pd.Timestamp('2024-01-03 14:29:00', tz='UTC'), False),
        (pd.Timestamp('2024-01-03 14:30:00', tz='UTC'), True),
        (pd.Timestamp('2024-01-03 20:59:00', tz='UTC'), True),
        (pd.Timestamp('2024-01-03 21:00:00', tz='UTC'), False),
    ]
)
def test_simulated_exchange_uses_open_closed_half_open_interval(dt, expected):
    """
    Market hours should be open at the start time and closed at the end time.
    """
    exchange = SimulatedExchange(UTC_START_DT)

    assert exchange.is_open_at_datetime(dt) is expected


@pytest.mark.parametrize(
    'dt',
    [
        pd.Timestamp('2024-01-06 15:00:00', tz='UTC'),
        pd.Timestamp('2024-01-07 15:00:00', tz='UTC'),
    ]
)
def test_simulated_exchange_is_closed_on_weekends(dt):
    """
    Weekend timestamps should always be treated as closed.
    """
    exchange = SimulatedExchange(UTC_START_DT)

    assert not exchange.is_open_at_datetime(dt)


def test_simulated_exchange_localises_naive_timestamps_to_utc():
    """
    Naive timestamps are interpreted as UTC before market-hours checks.
    """
    exchange = SimulatedExchange(UTC_START_DT)

    assert exchange.is_open_at_datetime(pd.Timestamp('2024-01-03 14:30:00'))
    assert not exchange.is_open_at_datetime(pd.Timestamp('2024-01-03 21:00:00'))


@pytest.mark.parametrize(
    'dt,expected',
    [
        (pd.Timestamp('2024-01-03 09:30:00', tz='US/Eastern'), True),
        (pd.Timestamp('2024-01-03 16:00:00', tz='US/Eastern'), False),
    ]
)
def test_simulated_exchange_converts_non_utc_aware_timestamps_before_comparison(dt, expected):
    """
    Timezone-aware timestamps in non-UTC zones should be converted to UTC
    before being compared against market hours.
    """
    exchange = SimulatedExchange(UTC_START_DT)

    assert exchange.is_open_at_datetime(dt) is expected

