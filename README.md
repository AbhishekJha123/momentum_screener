# Stock Scanner for Small Cap NASDAQ Stocks

This Python script scans NASDAQ-listed small-cap stocks for specific trading signals based on price, volume, and percentage price change. It leverages multithreading to efficiently filter small-cap stocks and then monitors live intraday trading data to alert when certain criteria are met.

---

## Features

- Downloads and filters NASDAQ ticker symbols for **small-cap stocks** (market cap < $2 billion).
- Multithreaded fetching of market caps for improved performance.
- Scans filtered stocks in real-time during market hours.
- Alerts when a stock meets the following criteria:
  - Current price between $1 and $200
  - Shares outstanding less than or equal to 200 million
  - Percentage price change greater than 5%
  - Relative volume (current volume / average volume) greater than 5x
- Logs scanning activity to both console and `stock_scanner.log`.
- Handles market open hours including pre-market and after-hours sessions.
- Uses `yfinance` for data retrieval and `tqdm` for progress bars.

---

## Installation

Make sure you have Python 3.7+ installed. Then install the required dependencies:

```bash
pip install yfinance pandas tqdm pytz certifi
