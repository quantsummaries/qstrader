#!/usr/bin/env python

# Script to demonstrate the examples in Chapter 25 of Advanced Algorithmic Trading, by Michael L. Halls-Moore.

import sys
import subprocess


if __name__ == "__main__":
    # download the latest data for the symbols used in the examples
    # SPY: SPDR S&P 500 ETF
    # IJS: iShares S&P Small-Cap 600 Value ETF
    # EFA: iShares MSCI EAFE ETF
    # EEM: iShares MSCI Emerging Markets ETF
    # AGG: iShares Core U.S. Aggregate Bond ETF
    # JNK: SPDR Bloomberg Barclays High Yield Bond ETF
    # DJP: iPath Bloomberg Commodity Index Total Return ETN
    # RWR: SPDR Dow Jones REIT ETF

    subprocess.run(
        [sys.executable, "../scripts/qst_download_data.py", "-s", "SPY,IJS,EFA,EEM,AGG,JNK,DJP,RWR", "-dd", "../data/"])

    start_dates = {'SPY': '2003-09-29',
                   'IJS': '2007-12-04',
                   'EFA': '2007-12-04',
                   'EEM': '2007-12-04',
                   'AGG': '2003-09-29',
                   'JNK': '2007-12-04',
                   'DJP': '2007-12-04',
                   'RWR': '2007-12-04'}

    end_dates = {'SPY': '2016-10-12',
                 'IJS': '2016-10-12',
                 'EFA': '2016-10-12',
                 'EEM': '2016-10-12',
                 'AGG': '2016-10-12',
                 'JNK': '2016-10-12',
                 'DJP': '2016-10-12',
                 'RWR': '2016-10-12'}


    # 1 - US Equities/Bonds 60/40 Mix ETF Strategy
    start_dt = max(start_dates['SPY'], start_dates['AGG'])
    end_dt = min(end_dates['SPY'], end_dates['AGG'])
    subprocess.run([sys.executable, "../scripts/qst_static_alloc.py",
                    "-sd", start_dt,
                    "-ed", end_dt,
                    "-s", "SPY,AGG",
                    "-sa", "0.6,0.4",
                    "-sf", "end_of_month",
                    "-b", "SPY",
                    "-ba", "1.0",
                    "-bf", "buy_and_hold",
                    "-dd", "../data/",
                    "-t", "US Equities/Bonds 60/40 Mix ETF Strategy"],
                   )

    # 2 - Strategic Weight ETF Strategy
    start_dt = max(start_dates['SPY'],
                   start_dates['IJS'],
                   start_dates['EFA'],
                   start_dates['EEM'],
                   start_dates['AGG'],
                   start_dates['JNK'],
                   start_dates['DJP'],
                   start_dates['RWR'])
    end_dt = max(end_dates['SPY'],
                 end_dates['IJS'],
                 end_dates['EFA'],
                 end_dates['EEM'],
                 end_dates['AGG'],
                 end_dates['JNK'],
                 end_dates['DJP'],
                 end_dates['RWR'])
    subprocess.run([sys.executable, "../scripts/qst_static_alloc.py",
                    "-sd", start_dt,
                    "-ed", end_dt,
                    "-s", "SPY,IJS,EFA,EEM,AGG,JNK,DJP,RWR",
                    "-sa", "0.25,0.05,0.2,0.05,0.2,0.05,0.1,0.1",
                    "-sf", "end_of_month",
                    "-b", "SPY",
                    "-ba", "1.0",
                    "-bf", "buy_and_hold",
                    "-dd", "../data/",
                    "-t", "Strategic Weight ETF Strategy"],)

    # 3- Equal Weight ETF Strategy
    subprocess.run([sys.executable, "../scripts/qst_static_alloc.py",
                    "-sd", start_dt,
                    "-ed", end_dt,
                    "-s", "SPY,IJS,EFA,EEM,AGG,JNK,DJP,RWR",
                    "-sa", "0.125,0.125,0.125,0.125,0.125,0.125,0.125,0.125",
                    "-sf", "end_of_month",
                    "-b", "SPY",
                    "-ba", "1.0",
                    "-bf", "buy_and_hold",
                    "-dd", "../data/",
                    "-t", "Equal Weight ETF Strategy"])
