# Testing and Documentation

## TODO: alpha_model

## asset

- [x] asset.py::Asset, abstract class that stores meta data about a trading asset.
- cash.py::Cash, subclass of Asset that represents cash as a trading asset.
- equity.py::Equity, subclass of Asset that stores meta data about an equity common stock or ETF.

- [x] universe::Universe, interface specification for an Asset Universe. 
- dynamic.py::DynamicUniverse, subclass of Universe that that allows additions of assets beyond a certain datetime.
- static.py::StaticUniverse, subclass of Universe that does not change its composition through time.

- [x] tests -> unit -> asset

## TODO: broker

## NEXT: data

## TODO: exchange

## TODO: execution

## TODO: portcon

## TODO: risk_model

## TODO: signals

## TODO: simulation

## TODO: statistics

## TODO: system

## TODO: trading

## TODO: utils