from matplotlib.ticker import FuncFormatter
from matplotlib import cm
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns

import qstrader.statistics.performance as perf
from qstrader.statistics.statistics import Statistics
from qstrader import settings


class TearsheetStatistics(Statistics):
    """
    Displays a Matplotlib-generated 'one-pager' as often
    found in institutional strategy performance reports.
    """
    def __init__(
        self,
        strategy_equity,
        benchmark_equity=None,
        title=None,
        periods=252
    ):
        self.strategy_equity = strategy_equity
        self.benchmark_equity = benchmark_equity
        self.title = title
        self.periods = periods

    def get_results(self, equity_df):
        """
        Return a dict with all important results & stats.
        """
        # Returns
        equity_df["returns"] = equity_df["Equity"].pct_change().fillna(0.0)

        # Cummulative Returns
        equity_df["cum_returns"] = np.exp(np.log(1 + equity_df["returns"]).cumsum())

        # Drawdown, max drawdown, max drawdown duration
        dd_s, max_dd, dd_dur = perf.create_drawdowns(equity_df["cum_returns"])

        # Equity statistics
        statistics = {}
        statistics["sharpe"] = perf.create_sharpe_ratio(
            equity_df["returns"], self.periods
        )
        statistics["drawdowns"] = dd_s
        statistics["max_drawdown"] = max_dd
        statistics["max_drawdown_pct"] = max_dd
        statistics["max_drawdown_duration"] = dd_dur
        statistics["equity"] = equity_df["Equity"]
        statistics["returns"] = equity_df["returns"]
        statistics["cum_returns"] = equity_df["cum_returns"]
        return statistics

    @staticmethod
    def _calculate_trade_returns(returns) -> np.ndarray:
        """
        Aggregate period returns into synthetic trade returns by summing
        consecutive non-zero returns with the same sign.
        """
        returns_array = returns.dropna().values
        if len(returns_array) == 0:
            return np.array([])

        trade_returns = []
        current_trade = 0.0
        current_sign = 0

        for ret in returns_array:
            if ret == 0:
                if current_trade != 0.0:
                    trade_returns.append(current_trade)
                    current_trade = 0.0
                    current_sign = 0
                continue

            sign = int(np.sign(ret))
            if current_sign != 0 and sign != current_sign:
                trade_returns.append(current_trade)
                current_trade = 0.0

            current_trade += ret
            current_sign = sign

        if current_trade != 0.0:
            trade_returns.append(current_trade)

        return np.array(trade_returns)

    def _plot_equity(self, strat_stats, bench_stats=None, ax=None, **kwargs):
        """
        Plots cumulative rolling returns versus some benchmark.
        """
        def format_two_dec(x, pos):
            return '%.2f' % x

        equity = strat_stats['cum_returns']

        if ax is None:
            ax = plt.gca()

        y_axis_formatter = FuncFormatter(format_two_dec)
        ax.yaxis.set_major_formatter(FuncFormatter(y_axis_formatter))
        ax.xaxis.set_tick_params(reset=True)
        ax.yaxis.grid(linestyle=':')
        ax.xaxis.set_major_locator(mdates.YearLocator(1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.grid(linestyle=':')

        equity.plot(lw=2, color='green', alpha=0.6, x_compat=False,
                    label='Strategy', ax=ax, **kwargs)
        if bench_stats is not None:
            bench_stats['cum_returns'].plot(
                lw=2, color='gray', alpha=0.6, x_compat=False,
                label='Benchmark', ax=ax, **kwargs
            )

        ax.axhline(1.0, linestyle='--', color='black', lw=1)
        ax.set_ylabel('Cumulative returns')
        ax.legend(loc='best')
        ax.set_xlabel('')
        plt.setp(ax.get_xticklabels(), visible=True, rotation=0, ha='center')
        return ax

    def _plot_drawdown(self, stats, ax=None, **kwargs):
        """
        Plots the underwater curve
        """
        def format_perc(x, pos):
            return '%.0f%%' % x

        drawdown = stats['drawdowns']

        if ax is None:
            ax = plt.gca()

        y_axis_formatter = FuncFormatter(format_perc)
        ax.yaxis.set_major_formatter(FuncFormatter(y_axis_formatter))
        ax.yaxis.grid(linestyle=':')
        ax.xaxis.set_tick_params(reset=True)
        ax.xaxis.set_major_locator(mdates.YearLocator(1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.grid(linestyle=':')

        underwater = -100 * drawdown
        underwater.plot(ax=ax, lw=2, kind='area', color='red', alpha=0.3, **kwargs)
        ax.set_ylabel('')
        ax.set_xlabel('')
        plt.setp(ax.get_xticklabels(), visible=True, rotation=0, ha='center')
        ax.set_title('Drawdown (%)', fontweight='bold')
        return ax

    def _plot_monthly_returns(self, stats, ax=None, **kwargs):
        """
        Plots a heatmap of the monthly returns.
        """
        returns = stats['returns']
        if ax is None:
            ax = plt.gca()

        monthly_ret = perf.aggregate_returns(returns, 'monthly')
        monthly_ret = monthly_ret.unstack()
        monthly_ret = np.round(monthly_ret, 3)
        monthly_ret.rename(
            columns={1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
                     5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
                     9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'},
            inplace=True
        )

        sns.heatmap(
            monthly_ret.fillna(0) * 100.0,
            annot=True,
            fmt="0.1f",
            annot_kws={"size": 8},
            alpha=1.0,
            center=0.0,
            cbar=False,
            cmap=cm.RdYlGn,
            ax=ax, **kwargs)
        ax.set_title('Monthly Returns (%)', fontweight='bold')
        ax.set_ylabel('')
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
        ax.set_xlabel('')

        return ax

    def _plot_yearly_returns(self, stats, ax=None, **kwargs):
        """
        Plots a barplot of returns by year.
        """
        def format_perc(x, pos):
            return '%.0f%%' % x

        returns = stats['returns']

        if ax is None:
            ax = plt.gca()

        y_axis_formatter = FuncFormatter(format_perc)
        ax.yaxis.set_major_formatter(FuncFormatter(y_axis_formatter))
        ax.yaxis.grid(linestyle=':')

        yly_ret = perf.aggregate_returns(returns, 'yearly') * 100.0
        yly_ret.plot(ax=ax, kind="bar")
        ax.set_title('Yearly Returns (%)', fontweight='bold')
        ax.set_ylabel('')
        ax.set_xlabel('')
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
        ax.xaxis.grid(False)

        return ax

    def _plot_txt_curve(self, stats, bench_stats=None, ax=None, **kwargs):
        """
        Outputs the statistics for the equity curve.
        """
        def format_perc(x, pos):
            return '%.0f%%' % x

        if ax is None:
            ax = plt.gca()

        y_axis_formatter = FuncFormatter(format_perc)
        ax.yaxis.set_major_formatter(FuncFormatter(y_axis_formatter))

        # Strategy statistics
        returns = stats["returns"]
        cum_returns = stats['cum_returns']
        tot_ret = cum_returns.iloc[-1] - 1.0
        cagr = perf.create_cagr(cum_returns, self.periods)
        sharpe = perf.create_sharpe_ratio(returns, self.periods)
        sortino = perf.create_sortino_ratio(returns, self.periods)
        dd, dd_max, dd_dur = perf.create_drawdowns(cum_returns)

        # Calculate trades per year from synthetic sign-consistent trade runs.
        trade_returns = self._calculate_trade_returns(returns)

        num_trades = len(trade_returns)
        years = len(returns) / float(self.periods)
        trd_yr = num_trades / years if years > 0 else 0

        # Benchmark statistics
        if bench_stats is not None:
            bench_returns = bench_stats["returns"]
            bench_cum_returns = bench_stats['cum_returns']
            bench_tot_ret = bench_cum_returns.iloc[-1] - 1.0
            bench_cagr = perf.create_cagr(bench_cum_returns, self.periods)
            bench_sharpe = perf.create_sharpe_ratio(bench_returns, self.periods)
            bench_sortino = perf.create_sortino_ratio(bench_returns, self.periods)
            bench_dd, bench_dd_max, bench_dd_dur = perf.create_drawdowns(bench_cum_returns)

        # Strategy Values
        ax.text(7.50, 8.2, 'Strategy', fontweight='bold', horizontalalignment='right', fontsize=8, color='green')

        ax.text(0.25, 6.9, 'Total Return', fontsize=8)
        ax.text(7.50, 6.9, '{:.0%}'.format(tot_ret), fontweight='bold', horizontalalignment='right', fontsize=8)

        ax.text(0.25, 5.9, 'CAGR', fontsize=8)
        ax.text(7.50, 5.9, '{:.2%}'.format(cagr), fontweight='bold', horizontalalignment='right', fontsize=8)

        ax.text(0.25, 4.9, 'Sharpe Ratio', fontsize=8)
        ax.text(7.50, 4.9, '{:.2f}'.format(sharpe), fontweight='bold', horizontalalignment='right', fontsize=8)

        ax.text(0.25, 3.9, 'Sortino Ratio', fontsize=8)
        ax.text(7.50, 3.9, '{:.2f}'.format(sortino), fontweight='bold', horizontalalignment='right', fontsize=8)

        ax.text(0.25, 2.9, 'Annual Volatility', fontsize=8)
        ax.text(7.50, 2.9, '{:.2%}'.format(returns.std() * np.sqrt(252)), fontweight='bold', horizontalalignment='right', fontsize=8)

        ax.text(0.25, 1.9, 'Max Daily Drawdown', fontsize=8)
        ax.text(7.50, 1.9, '{:.2%}'.format(dd_max), color='red', fontweight='bold', horizontalalignment='right', fontsize=8)

        ax.text(0.25, 0.9, 'Trades per Year', fontsize=8)
        ax.text(7.50, 0.9, '{:.1f}'.format(trd_yr), fontweight='bold', horizontalalignment='right', fontsize=8)

        # Benchmark Values
        if bench_stats is not None:
            ax.text(10.0, 8.2, 'Benchmark', fontweight='bold', horizontalalignment='right', fontsize=8, color='gray')
            ax.text(10.0, 6.9, '{:.0%}'.format(bench_tot_ret), fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.text(10.0, 5.9, '{:.2%}'.format(bench_cagr), fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.text(10.0, 4.9, '{:.2f}'.format(bench_sharpe), fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.text(10.0, 3.9, '{:.2f}'.format(bench_sortino), fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.text(10.0, 2.9, '{:.2%}'.format(bench_returns.std() * np.sqrt(252)), fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.text(10.0, 1.9, '{:.2%}'.format(bench_dd_max), color='red', fontweight='bold', horizontalalignment='right', fontsize=8)
            ax.set_title('Curve vs. Benchmark', fontweight='bold')
        else:
            ax.set_title('Equity Curve', fontweight='bold')

        ax.grid(False)
        ax.spines['top'].set_linewidth(2.0)
        ax.spines['bottom'].set_linewidth(2.0)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.get_xaxis().set_visible(False)
        ax.set_ylabel('')
        ax.set_xlabel('')

        ax.axis([0, 10, 0, 10])
        return ax

    def _plot_txt_trade(self, stats, ax=None, **kwargs):
        """
        Outputs the statistics for the trades. Referenced https://github.com/mhallsmoore/qstrader/blob/advanced-algorithmic-trading/qstrader/statistics/tearsheet.py and need
        a code review. See docs/legacy/*.md for details.
        """
        def format_perc(x, pos):
            return '%.0f%%' % x

        if ax is None:
            ax = plt.gca()

        returns = stats["returns"]
        
        # A "trade" is a run of consecutive non-zero returns with identical sign.
        trade_returns = self._calculate_trade_returns(returns)

        # Calculate trade metrics
        if len(trade_returns) > 0:
            num_trades = len(trade_returns)
            winning_trades = trade_returns[trade_returns > 0]
            losing_trades = trade_returns[trade_returns < 0]
            
            win_pct = len(winning_trades) / float(num_trades)
            win_pct_str = '{:.0%}'.format(win_pct)
            avg_trd_pct = '{:.2%}'.format(np.mean(trade_returns))
            avg_win_pct = '{:.2%}'.format(np.mean(winning_trades)) if len(winning_trades) > 0 else "N/A"
            avg_loss_pct = '{:.2%}'.format(np.mean(losing_trades)) if len(losing_trades) > 0 else "N/A"
            max_win_pct = '{:.2%}'.format(np.max(trade_returns))
            max_loss_pct = '{:.2%}'.format(np.min(trade_returns))
        else:
            num_trades = 0
            win_pct_str = "N/A"
            avg_trd_pct = "N/A"
            avg_win_pct = "N/A"
            avg_loss_pct = "N/A"
            max_win_pct = "N/A"
            max_loss_pct = "N/A"

        max_loss_dt = 'TBD'
        avg_dit = '0.0'

        y_axis_formatter = FuncFormatter(format_perc)
        ax.yaxis.set_major_formatter(FuncFormatter(y_axis_formatter))

        ax.text(0.5, 8.9, 'Trade Winning %', fontsize=8)
        ax.text(9.5, 8.9, win_pct_str, fontsize=8, fontweight='bold', horizontalalignment='right')

        ax.text(0.5, 7.9, 'Average Trade %', fontsize=8)
        ax.text(9.5, 7.9, avg_trd_pct, fontsize=8, fontweight='bold', horizontalalignment='right')

        ax.text(0.5, 6.9, 'Average Win %', fontsize=8)
        color = 'green' if avg_win_pct != "N/A" and float(avg_win_pct.rstrip('%')) >= 0 else 'red'
        ax.text(9.5, 6.9, avg_win_pct, fontsize=8, fontweight='bold', color=color, horizontalalignment='right')

        ax.text(0.5, 5.9, 'Average Loss %', fontsize=8)
        color = 'red' if avg_loss_pct != "N/A" else 'black'
        ax.text(9.5, 5.9, avg_loss_pct, fontsize=8, fontweight='bold', color=color, horizontalalignment='right')

        ax.text(0.5, 4.9, 'Best Trade %', fontsize=8)
        ax.text(9.5, 4.9, max_win_pct, fontsize=8, fontweight='bold', color='green', horizontalalignment='right')

        ax.text(0.5, 3.9, 'Worst Trade %', fontsize=8)
        ax.text(9.5, 3.9, max_loss_pct, color='red', fontsize=8, fontweight='bold', horizontalalignment='right')

        ax.text(0.5, 2.9, 'Worst Trade Date', fontsize=8)
        ax.text(9.5, 2.9, max_loss_dt, fontsize=8, fontweight='bold', horizontalalignment='right')

        ax.text(0.5, 1.9, 'Avg Days in Trade', fontsize=8)
        ax.text(9.5, 1.9, avg_dit, fontsize=8, fontweight='bold', horizontalalignment='right')

        ax.text(0.5, 0.9, 'Trades', fontsize=8)
        ax.text(9.5, 0.9, '{:.0f}'.format(num_trades), fontsize=8, fontweight='bold', horizontalalignment='right')

        ax.set_title('Trade', fontweight='bold')
        ax.grid(False)
        ax.spines['top'].set_linewidth(2.0)
        ax.spines['bottom'].set_linewidth(2.0)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.get_xaxis().set_visible(False)
        ax.set_ylabel('')
        ax.set_xlabel('')

        ax.axis([0, 10, 0, 10])
        return ax

    def _plot_txt_time(self, stats, ax=None, **kwargs):
        """
        Outputs the statistics for various time frames. Referenced legacy code https://github.com/mhallsmoore/qstrader/blob/advanced-algorithmic-trading/qstrader/statistics/tearsheet.py and need
        a code review. See docs/legacy/*.md for details.
        """
        def format_perc(x, pos):
            return '%.0f%%' % x

        returns = stats['returns']

        if ax is None:
            ax = plt.gca()

        y_axis_formatter = FuncFormatter(format_perc)
        ax.yaxis.set_major_formatter(FuncFormatter(y_axis_formatter))

        mly_ret = perf.aggregate_returns(returns, 'monthly')
        yly_ret = perf.aggregate_returns(returns, 'yearly')

        mly_pct = mly_ret[mly_ret >= 0].shape[0] / float(mly_ret.shape[0])
        mly_avg_win_pct = np.mean(mly_ret[mly_ret >= 0])
        mly_avg_loss_pct = np.mean(mly_ret[mly_ret < 0])
        mly_max_win_pct = np.max(mly_ret)
        mly_max_loss_pct = np.min(mly_ret)
        yly_pct = yly_ret[yly_ret >= 0].shape[0] / float(yly_ret.shape[0])
        yly_max_win_pct = np.max(yly_ret)
        yly_max_loss_pct = np.min(yly_ret)

        ax.text(0.5, 8.9, 'Winning Months %', fontsize=8)
        ax.text(9.5, 8.9, '{:.0%}'.format(mly_pct), fontsize=8, fontweight='bold',
                horizontalalignment='right')

        ax.text(0.5, 7.9, 'Average Winning Month %', fontsize=8)
        ax.text(9.5, 7.9, '{:.2%}'.format(mly_avg_win_pct), fontsize=8, fontweight='bold',
                color='red' if mly_avg_win_pct < 0 else 'green',
                horizontalalignment='right')

        ax.text(0.5, 6.9, 'Average Losing Month %', fontsize=8)
        ax.text(9.5, 6.9, '{:.2%}'.format(mly_avg_loss_pct), fontsize=8, fontweight='bold',
                color='red' if mly_avg_loss_pct < 0 else 'green',
                horizontalalignment='right')

        ax.text(0.5, 5.9, 'Best Month %', fontsize=8)
        ax.text(9.5, 5.9, '{:.2%}'.format(mly_max_win_pct), fontsize=8, fontweight='bold',
                color='red' if mly_max_win_pct < 0 else 'green',
                horizontalalignment='right')

        ax.text(0.5, 4.9, 'Worst Month %', fontsize=8)
        ax.text(9.5, 4.9, '{:.2%}'.format(mly_max_loss_pct), fontsize=8, fontweight='bold',
                color='red' if mly_max_loss_pct < 0 else 'green',
                horizontalalignment='right')

        ax.text(0.5, 3.9, 'Winning Years %', fontsize=8)
        ax.text(9.5, 3.9, '{:.0%}'.format(yly_pct), fontsize=8, fontweight='bold',
                horizontalalignment='right')

        ax.text(0.5, 2.9, 'Best Year %', fontsize=8)
        ax.text(9.5, 2.9, '{:.2%}'.format(yly_max_win_pct), fontsize=8,
                fontweight='bold', color='red' if yly_max_win_pct < 0 else 'green',
                horizontalalignment='right')

        ax.text(0.5, 1.9, 'Worst Year %', fontsize=8)
        ax.text(9.5, 1.9, '{:.2%}'.format(yly_max_loss_pct), fontsize=8,
                fontweight='bold', color='red' if yly_max_loss_pct < 0 else 'green',
                horizontalalignment='right')

        ax.set_title('Time', fontweight='bold')

        ax.grid(False)
        ax.spines['top'].set_linewidth(2.0)
        ax.spines['bottom'].set_linewidth(2.0)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.get_yaxis().set_visible(False)
        ax.get_xaxis().set_visible(False)
        ax.set_ylabel('')
        ax.set_xlabel('')

        ax.axis([0, 10, 0, 10])
        return ax

    def plot_results(self, filename=None):
        """
        Plot the Tearsheet

        Parameters
        ==========
        filename : `str`
            Option to save the tearsheet output when a filename is specified.
        """
        rc = {
            'lines.linewidth': 1.0,
            'axes.facecolor': '0.995',
            'figure.facecolor': '0.97',
            'font.family': 'serif',
            'font.serif': 'Ubuntu',
            'font.monospace': 'Ubuntu Mono',
            'font.size': 10,
            'axes.labelsize': 10,
            'axes.labelweight': 'bold',
            'axes.titlesize': 10,
            'xtick.labelsize': 8,
            'ytick.labelsize': 8,
            'legend.fontsize': 10,
            'figure.titlesize': 12
        }
        sns.set_context(rc)
        sns.set_style("whitegrid")
        sns.set_palette("deep", desat=.6)

        vertical_sections = 5
        fig = plt.figure(figsize=(16, 12))
        fig.suptitle(self.title, y=0.94, weight='bold')
        gs = gridspec.GridSpec(vertical_sections, 3, wspace=0.25, hspace=0.5)

        stats = self.get_results(self.strategy_equity)
        bench_stats = None
        if self.benchmark_equity is not None:
            bench_stats = self.get_results(self.benchmark_equity)

        ax_equity = plt.subplot(gs[:2, :])
        ax_drawdown = plt.subplot(gs[2, :])
        ax_monthly_returns = plt.subplot(gs[3, :2])
        ax_yearly_returns = plt.subplot(gs[3, 2])
        ax_txt_curve = plt.subplot(gs[4, 0])
        ax_txt_trade = plt.subplot(gs[4, 1])
        ax_txt_time = plt.subplot(gs[4, 2])

        self._plot_equity(stats, bench_stats=bench_stats, ax=ax_equity)
        self._plot_drawdown(stats, ax=ax_drawdown)
        self._plot_monthly_returns(stats, ax=ax_monthly_returns)
        self._plot_yearly_returns(stats, ax=ax_yearly_returns)
        self._plot_txt_curve(stats, bench_stats=bench_stats, ax=ax_txt_curve)
        self._plot_txt_trade(stats, ax=ax_txt_trade)
        self._plot_txt_time(stats, ax=ax_txt_time)

        # Save the figure
        if filename:
            if settings.PRINT_EVENTS:
                print(f"Saving tearsheet to {filename}")
            fig = plt.gcf()    
            fig.savefig(filename)

        # Plot the figure
        if settings.PRINT_EVENTS:
            print('Plotting the tearsheet...')
        plt.show()

    def save(self, filename: str) -> None:
        """
        Save statistics results to filename
        """
        pass

    def update(self, dt: pd.Timestamp) -> None:
        """
        Update all the statistics according to values of the portfolio
        and open positions. This should be called from within the
        event loop.
        """
        pass