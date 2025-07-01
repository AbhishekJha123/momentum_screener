import yfinance as yf
import pandas as pd
import time
import logging
from datetime import datetime
import warnings
import ssl
import certifi
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("stock_scanner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Parameters
MIN_PRICE = 1
MAX_PRICE = 200
MAX_SHARES = 20e7  # 200 million shares
MIN_REL_VOLUME = 5
MIN_PCT_CHANGE = 5
SMALL_CAP_MAX = 2e9  # 2 billion USD max for small cap
MAX_WORKERS = 10 

# --- Step 1: Multithreaded fetch and save small caps ---

def fetch_market_cap(ticker):
    try:
        info = yf.Ticker(ticker).info
        market_cap = info.get('marketCap', 0)
        if market_cap and market_cap < SMALL_CAP_MAX:
            return ticker
    except Exception:
        return None

def fetch_and_save_small_caps():
    logger.info("Downloading NASDAQ ticker list...")
    try:
        url = "https://raw.githubusercontent.com/datasets/nasdaq-listings/master/data/nasdaq-listed-symbols.csv"
        df = pd.read_csv(url)
        tickers = df['Symbol'].tolist()
        logger.info(f"Loaded {len(tickers)} tickers from NASDAQ listings")
    except Exception as e:
        logger.error(f"Failed to download NASDAQ tickers: {e}")
        return

    small_caps = []
    logger.info("Filtering small cap stocks (< $2B market cap) with multithreading...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_market_cap, ticker): ticker for ticker in tickers}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Filtering small caps"):
            ticker = future.result()
            if ticker:
                small_caps.append(ticker)

    logger.info(f"Found {len(small_caps)} small cap tickers")

    with open('small_caps.txt', 'w') as f:
        for t in small_caps:
            f.write(t + '\n')

    logger.info("Saved small_caps.txt")

# --- Step 2: Read tickers from saved file ---

def get_active_stocks():
    try:
        with open('small_caps.txt', 'r') as f:
            tickers = [line.strip() for line in f.readlines()]
        logger.info(f"Loaded {len(tickers)} small-cap tickers from file")
        return tickers
    except Exception as e:
        logger.error(f"Failed to load tickers from file: {e}")
        return []

# --- Existing helper functions ---

def get_outstanding_shares(ticker):
    try:
        stock = yf.Ticker(ticker)
        shares = stock.info.get('sharesOutstanding', float('inf'))
        return float(shares) if shares is not None else float('inf')
    except Exception as e:
        logger.warning(f"Shares outstanding fetch error for {ticker}: {str(e)}")
        return float('inf')

def get_historical_volume(ticker):
    try:
        hist = yf.download(ticker, period="1mo", progress=False, auto_adjust=False)
        if hist.empty or 'Volume' not in hist.columns:
            return 0.0

        volume_data = hist['Volume']

        if isinstance(volume_data, pd.DataFrame):
            volume_data = volume_data.iloc[:, 0]

        avg_vol = pd.to_numeric(volume_data, errors='coerce').mean()

        if pd.isna(avg_vol):
            return 0.0

        return float(avg_vol)

    except Exception as e:
        logger.warning(f"Volume error for {ticker}: {str(e)}")
        return 0.0

def scan_stocks():
    symbols = get_active_stocks()
    if not symbols:
        logger.error("No stock symbols retrieved, aborting scan.")
        return

    logger.info(f"Scanning {len(symbols)} stocks...")

    for symbol in tqdm(symbols):
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period='1d', interval='1m')
            if data.empty:
                continue

            current_price = float(data['Close'].iloc[-1])
            current_volume = float(data['Volume'].iloc[-1])
            prev_close = float(data['Close'].iloc[0])

            pct_change = ((current_price - prev_close) / prev_close) * 100
            shares_outstanding = get_outstanding_shares(symbol)
            avg_volume = get_historical_volume(symbol)
            rel_volume = (current_volume / avg_volume) if avg_volume > 0 else 0

            if (MIN_PRICE <= current_price <= MAX_PRICE and
                shares_outstanding <= MAX_SHARES and
                pct_change >= MIN_PCT_CHANGE and
                rel_volume >= MIN_REL_VOLUME):

                logger.info(
                    f"ALERT: {symbol} | "
                    f"Price: ${current_price:.2f} | "
                    f"Change: {pct_change:.2f}% | "
                    f"Rel Vol: {rel_volume:.1f}x | "
                    f"Shares: {shares_outstanding/1e6:.2f}M"
                )

        except Exception as e:
            logger.error(f"Error processing {symbol}: {str(e)}")
            time.sleep(2)



def is_market_open():
    et = pytz.timezone('US/Eastern')
    now = datetime.now(et)

    if now.weekday() >= 5:  # Saturday or Sunday
        return False

    current_time = now.time()

    # Define market session time intervals as (start, end)
    sessions = [
        (time(4, 0), time(9, 30)),   # Pre-market
        (time(9, 30), time(16, 0)),  # Regular market
        (time(16, 0), time(20, 0))   # After-hours
    ]

    return any(start <= current_time < end for start, end in sessions)

def main():
    # Run this once to generate the small cap list, then comment it out
    # fetch_and_save_small_caps()

    logger.info("Starting stock scanner...")
    while True:
        if is_market_open():
            scan_stocks()
            logger.info("Scan completed. Waiting 5 minutes for next run...")
        else:
            logger.info("Market closed. Waiting for next open market hour...")
        time.sleep(300)

if __name__ == "__main__":
    main()
