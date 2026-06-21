import datetime

import pandas as pd

from qstrader.exchange.exchange import Exchange


class SimulatedExchange(Exchange):
    """
    The SimulatedExchange class is used to model a live
    trading venue.

    It exposes methods to inform a client class intance of
    when the exchange is open to determine when orders can
    be executed.

    Parameters
    ----------
    start_dt : `pd.Timestamp`
        The starting time of the simulated exchange.
    name : `str`, optional
        The name of the exchange, by default "NYSE".
    """

    def __init__(self, start_dt: pd.Timestamp,name: str="NYSE"):
        self.start_dt = start_dt
        self.name = name

        if self.name == 'NYSE':
            self.open_dt = datetime.time(14, 30, tzinfo=datetime.timezone.utc)
            self.close_dt = datetime.time(21, 00, tzinfo=datetime.timezone.utc)
        else:
            raise ValueError(f"Exchange {self.name} not supported in SimulatedExchange")

    def is_open_at_datetime(self, dt: pd.Timestamp) -> bool:
        """
        Check if the SimulatedExchange is open at a particular
        provided pandas Timestamp.

        This logic is simplistic in that it only checks whether
        the provided time is between market hours on a weekday.

        There is no historical calendar handling or concept of
        exchange holidays.

        Parameters
        ----------
        dt : `pd.Timestamp`
            The timestamp to check for open market hours.

        Returns
        -------
        `Boolean`
            Whether the exchange is open at this timestamp.
        """
        # ts.weekday() or ts.dayofweek: Returns the day of the week as an integer, where Monday = 0 and Sunday = 6.
        if dt.weekday() > 4:
            return False
        if dt.tzinfo is None:
            dt = dt.tz_localize('UTC')
        else:
            dt = dt.tz_convert('UTC')
        dt_time = dt.timetz()
        return self.open_dt <= dt_time and dt_time < self.close_dt
