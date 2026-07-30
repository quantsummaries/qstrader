#!/usr/bin/env python

# script of qstrader to download data

import argparse
import datetime
import os

import yfinance as yf

from qstrader.constants import DATA_DIR


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--symbols', type=str, required=True, help='Comma-separated symbols to download')
    parser.add_argument('-dd', '--data_dir', type=str, required=False, help='Path to data directory (default: DATA_DIR)', default=DATA_DIR)

    return parser.parse_args()

def file_exists(symbol: str) -> bool:
    """Check if the data file exists and the file's date is today."""
    file_path = os.path.join(DATA_DIR, f"{symbol}.csv")
    if not os.path.exists(file_path):
        return False

    file_date = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).date()
    tday = datetime.datetime.today().date()
    if file_date == tday:
        return True

    return False


if __name__ == "__main__":
    # example: uv run python qst_download.py -s VTI,CTA,GLD,SPY,AGG -dd ../data/

    args = parse_args()
    symbols = [x.upper() for x in args.symbols.split(',')]
    data_dir = args.data_dir

    for ticker in symbols:
        if file_exists(ticker):
            print(f"{ticker} already downloaded")
            continue
        stock = yf.Ticker(ticker)
        df = yf.download(ticker, period='max', auto_adjust=False)
        df.columns = df.columns.droplevel('Ticker')
        print(df.head())
        df.to_csv(os.path.join(data_dir, f"{ticker}.csv"), index=True)
