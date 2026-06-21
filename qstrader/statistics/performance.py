from itertools import groupby

import numpy as np
import pandas as pd


def aggregate_returns(returns: pd.Series, convert_to: str) -> pd.Series:
    """
    Aggregates returns by day, week, month, or year.
    Args:
        returns (pd.Series): A pandas Series representing period percentage returns, indexed by DatetimeIndex.
        convert_to (str): The desired frequency to convert the returns to.
            Options are 'weekly', 'monthly', or 'yearly'.
    Returns:
        pd.Series: A pandas Series with the aggregated returns at the specified frequency.
    """
    if not isinstance(returns.index, pd.DatetimeIndex):
        if pd.api.types.is_numeric_dtype(returns.index):
            raise TypeError('returns must be indexed by a pandas DatetimeIndex, got {}'.format(type(returns.index)))
        try:
            returns.index = pd.to_datetime(returns.index)
        except Exception:
            raise TypeError('returns must be indexed by a pandas DatetimeIndex, got {}'.format(type(returns.index)))

    def cumulate_returns(x: pd.Series) -> float:
        x = x.dropna()
        if x.empty:
            return np.nan
        return (1.0 + x).prod() - 1.0

    if convert_to not in {'weekly', 'monthly', 'yearly'}:
        raise ValueError(
            'convert_to must be weekly, monthly or yearly, instead got {}'.format(convert_to)
        )

    if convert_to == 'weekly':
        iso_calendar = returns.index.isocalendar()
        return returns.groupby([iso_calendar.year, iso_calendar.week]).apply(cumulate_returns)

    date_parts = returns.index.to_series()
    if convert_to == 'monthly':
        return returns.groupby([date_parts.dt.year, date_parts.dt.month]).apply(cumulate_returns)
    elif convert_to == 'yearly':
        return returns.groupby([date_parts.dt.year]).apply(cumulate_returns)
    else:
        raise ValueError(
            'convert_to must be weekly, monthly or yearly, instead got {}'.format(convert_to)
        )

def create_cagr(equity: pd.Series, periods: int=252) -> float:
    """
    Calculates the Compound Annual Growth Rate (CAGR)
    for the portfolio, by determining the number of years
    and then creating a compound annualised rate based
    on the total return.

    Parameters:
    equity - A pandas Series representing a cumulative equity curve
        (normalized cumulative returns starting at 1.0 or dollar-denominated
        equity starting at an initial portfolio value).
    periods - Daily (252), Hourly (252*6.5), Minutely(252*6.5*60) etc.
    """
    equity = equity.dropna()
    if equity.empty:
        raise ValueError("equity must contain at least one non-NaN value")

    start = equity.iloc[0]
    end = equity.iloc[-1]
    if start <= 0:
        raise ValueError("equity must start with a positive value")

    years = len(equity) / float(periods)
    return (end / start) ** (1.0 / years) - 1.0


def create_sharpe_ratio(returns: pd.Series, periods: int=252) -> float:
    """
    Create the Sharpe ratio for the strategy, based on a
    benchmark of zero (i.e. no risk-free rate information).

    Parameters:
    returns - A pandas Series representing period percentage returns.
    periods - Daily (252), Hourly (252*6.5), Minutely(252*6.5*60) etc.
    """
    return np.sqrt(periods) * (np.mean(returns)) / np.std(returns)


def create_sortino_ratio(returns: pd.Series, periods: int=252) -> float:
    """
    Create the Sortino ratio for the strategy, based on a
    benchmark of zero (i.e. no risk-free rate information).

    Parameters:
    returns - A pandas Series representing period percentage returns.
    periods - Daily (252), Hourly (252*6.5), Minutely(252*6.5*60) etc.
    """
    if len(returns[returns < 0]) <= 1:
        raise ValueError("Sortino ratio is undefined for returns with no negative values.")
    return np.sqrt(periods) * (np.mean(returns)) / np.std(returns[returns < 0])


def create_drawdowns(returns: pd.Series) -> tuple[pd.Series, float, int]:
    """
    Calculate the largest peak-to-trough drawdown of the equity curve
    as well as the duration of the drawdown. Requires that the
    pnl_returns is a pandas Series.

    Parameters:
        returns - A pandas Series representing period percentage returns.

    Returns:
        drawdown, drawdown_max, duration
    """
    # Calculate the cumulative returns curve
    # and set up the High Water Mark
    idx = returns.index
    hwm = np.zeros(len(idx))

    # Create the high water mark
    for t in range(1, len(idx)):
        hwm[t] = max(hwm[t - 1], returns.iloc[t])

    # Calculate the drawdown and duration statistics
    perf = pd.DataFrame(index=idx)
    perf["Drawdown"] = (hwm - returns) / hwm
    perf.loc[perf.index[0], 'Drawdown'] = 0.0
    perf["DurationCheck"] = np.where(perf["Drawdown"] == 0, 0, 1)
    duration = max(
        sum(1 for i in g if i == 1)
        for k, g in groupby(perf["DurationCheck"])
    )
    return perf["Drawdown"], np.max(perf["Drawdown"]), duration


if __name__ == '__main__':

    equity_series = pd.Series([100.0, 102.0, 101.5, 105.0, 108.0, 107.0])
    returns_series = equity_series.pct_change().fillna(0.0)
    cum_returns = np.exp(np.log(1 + returns_series).cumsum())

    cagr = create_cagr(equity_series, periods=252)
    sharpe = create_sharpe_ratio(returns_series, periods=252)
    sortino = create_sortino_ratio(returns_series, periods=252)
    dd_s, max_dd, max_dd_duration = create_drawdowns(cum_returns)

    print(f"CAGR: {cagr:.2%}, Sharpe: {sharpe:.2f}, Max DD: {max_dd:.2%}")