#!/usr/bin/env python

# script to download data

import os

import pandas as pd
import yfinance as yf

from qstrader.constants import DATA_DIR

for ticker in ['SPY', 'AGG', 'GLD', 'VTI', 'CTA', 'SGOV']:
    stock = yf.Ticker(ticker)
    df = yf.download(ticker, period='max', auto_adjust=False)
    df.columns = df.columns.droplevel('Ticker')
    print(df.head())
    df.to_csv(os.path.join(DATA_DIR, f"{ticker}.csv"), index=True)
