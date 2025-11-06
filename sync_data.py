import requests
import json
import os
import time
from datetime import datetime, timedelta

# --- Configuration ---
# API Keys are stored as GitHub Secrets
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")
DATA_DIR = "data"

# Finnhub Symbol Mapping (Adjusted for stability and to replace unsupported Mutual Funds with ETFs)
FINNHUB_SYMBOLS = {
    # Market Breadth (US) - Standard ETF tickers
    "SPY": "SPY",
    "QQQ": "QQQ",
    "DIA": "DIA",
    # Global Indices and VIX - Using confirmed Finnhub symbols
    "VIX": "VIX", 
    "HSI": "HSI", 
    "N225": "N225", 
    # Sector ETFs (11)
    "XLK": "XLK", "XLC": "XLC", "XLY": "XLY", "XLP": "XLP", "XLV": "XLV", "XLF": "XLF", 
    "XLE": "XLE", "XLI": "XLI", "XLB": "XLB", "XLU": "XLU", "VNQ": "VNQ",
    # Thematic/Commodity ETFs (4)
    "GLD": "GLD", "ROBO": "ROBO", "SMH": "SMH", "IWM": "IWM",
    # Money Market Funds (4) - Replaced unsupported Mutual Funds with highly liquid ETFs
    "VFIAX": "VOO",   # VOO (Vanguard S&P 500 ETF) replaces VFIAX
    "VTSAX": "VTI",   # VTI (Vanguard Total Stock Market ETF) replaces VTSAX
    "VBTLX": "BND",   # BND (Vanguard Total Bond Market ETF) replaces VBTLX
    "VMMXX": "BIL",   # BIL (SPDR Bloomberg 1-3 Month T-Bill ETF) replaces VMMXX
}

# List of symbols to fetch (keys from the mapping)
SYMBOLS_TO_FETCH = list(FINNHUB_SYMBOLS.keys())

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# --- Helper Functions ---

def save_json(data, filename):
    """Saves data to a JSON file in the data directory."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Successfully saved data to {path}")

def process_finnhub_data(symbol, raw_data):
    """
    Processes raw Finnhub time series data (candles) to calculate daily changes,
    and includes the critical division-by-zero check and 30-day truncation.
    """
    if not raw_data or raw_data.get('s') != 'ok' or not raw_data.get('c'):
        print(f"Warning: No valid Finnhub data found for {symbol}. Raw response: {raw_data}")
        return []

    # 'c' is close price, 't' is timestamp (epoch seconds)
    close_prices = raw_data['c']
    timestamps = raw_data['t']
    volumes = raw_data.get('v', [0] * len(close_prices)) # Volume might be missing for indices

    time_series_list = []
    for i in range(len(close_prices)):
        date_str = datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d')
        
        time_series_list.append({
            'date': date_str,
            'close': close_prices[i],
            'volume': volumes[i],
            'change_percent': 0.0,
            'volume_change_percent': 0.0,
        })

    # Sort the list by date ascending (Finnhub usually returns sorted, but for safety)
    time_series_list.sort(key=lambda x: x['date'])

    # Calculate daily changes
    for i in range(1, len(time_series_list)):
        current = time_series_list[i]
        previous = time_series_list[i-1]

        # --- Price Change Calculation with Division-by-Zero Check ---
        latest_close = current['close']
        previous_close = previous['close']
        
        if previous_close is not None and previous_close != 0:
            change_percent = ((latest_close - previous_close) / previous_close) * 100
            current['change_percent'] = round(change_percent, 2)
        else:
            current['change_percent'] = 0.0

        # --- Volume Change Calculation with Division-by-Zero Check ---
        latest_volume = current['volume']
        previous_volume = previous['volume']
        
        if previous_volume is not None and previous_volume != 0 and latest_volume != 0:
            volume_change = ((latest_volume - previous_volume) / previous_volume) * 100
            current['volume_change_percent'] = round(volume_change, 2)
        else:
            current['volume_change_percent'] = 0.0

    # Final Optimization: Only keep the latest 30 trading days for frontend display
    return time_series_list[-30:]

# --- Data Fetching Functions ---

def fetch_hibor_rates():
    """
    Fetches HIBOR rates from HKMA API using the daily figures endpoint.
    """
    print("Fetching HIBOR rates...")
    # New, more stable daily HIBOR API endpoint
    url = "https://api.hkma.gov.hk/public/market-data-and-statistics/market-data/interest-rate/hk-interbank-interest-rates-daily"
    
    try:
        response = requests.get(url, timeout=10 )
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('result') and data['result'].get('records'):
            # Get the latest record
            latest_record = data['result']['records'][0]
            
            # The daily API uses different keys, we map them to the expected frontend keys
            hibor_data = {
                "date": latest_record.get('end_of_day'),
                "ir_1m": latest_record.get('ir_1m'),
                "ir_3m": latest_record.get('ir_3m'),
                "ir_6m": latest_record.get('ir_6m'),
            }
            
            # Check if all required keys are present and valid
            if all(hibor_data.get(k) for k in ["ir_1m", "ir_3m", "ir_6m"]):
                save_json(hibor_data, "hibor_rates.json")
            else:
                print("Error: HKMA Daily API returned data but missing 1M, 3M, or 6M rates in the latest record.")
                
        else:
            print("Error: HKMA Daily API returned no records.")
            
    except requests.RequestException as e:
        print(f"Error fetching HIBOR rates: {e}. The API may be temporarily unavailable or the endpoint has changed.")

def fetch_fear_greed_index():
    """Fetches Fear & Greed Index from alternative.me API."""
    print("Fetching Fear & Greed Index...")
    url = "https://api.alternative.me/fng/?limit=30"
    
    try:
        response = requests.get(url, timeout=10 )
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('data'):
            history_data = sorted(data['data'], key=lambda x: int(x['timestamp']))
            
            formatted_data = []
            for record in history_data:
                date_str = datetime.fromtimestamp(int(record['timestamp'])).strftime('%Y-%m-%d')
                formatted_data.append({
                    "date": date_str,
                    "value": int(record['value']),
                    "sentiment": record['value_classification']
                })
            
            save_json(formatted_data, "market_sentiment_history.json")
        else:
            print("Error: Fear & Greed API returned no data.")
            
    except requests.RequestException as e:
        print(f"Error fetching Fear & Greed Index: {e}")

def fetch_market_data():
    """Fetches time series data for all configured symbols from Finnhub."""
    if not FINNHUB_API_KEY:
        print("Error: FINNHUB_API_KEY environment variable not set. Market data will not be updated.")
        return

    base_url = "https://finnhub.io/api/v1/stock/candle"
    
    # Calculate start and end time for the last 30 trading days (approx 45 calendar days )
    end_time = int(time.time())
    start_time = int((datetime.now() - timedelta(days=45)).timestamp())
    
    # Initialize data structures for combined output
    market_data_history = {}
    money_fund_data = {}

    for i, symbol in enumerate(SYMBOLS_TO_FETCH):
        finnhub_symbol = FINNHUB_SYMBOLS[symbol]
        print(f"Fetching data for {symbol} ({finnhub_symbol}) ({i+1}/{len(SYMBOLS_TO_FETCH)})...")
        
        params = {
            "symbol": finnhub_symbol,
            "resolution": "D", # Daily resolution
            "from": start_time,
            "to": end_time,
            "token": FINNHUB_API_KEY
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data.get('s') == 'ok':
                # Process and truncate the data
                processed_data = process_finnhub_data(symbol, data)
                
                # Separate data based on symbol type
                if symbol in ["VFIAX", "VTSAX", "VBTLX", "VMMXX"]:
                    # Money Fund Data: Only need the latest data point
                    if processed_data:
                        latest_data = processed_data[-1]
                        money_fund_data[symbol] = {
                            "date": latest_data['date'],
                            "close": latest_data['close'],
                            "change_percent": latest_data['change_percent']
                        }
                else:
                    # Market Breadth and Fund Flow Data: Need the 30-day history
                    market_data_history[symbol] = processed_data
            else:
                # Log the error message from Finnhub
                error_message = data.get('error', 'Unknown error')
                print(f"Finnhub API Error for {symbol} ({finnhub_symbol}): {error_message}")
                
                # Critical check: If the error is related to invalid symbol or API key, it will fail.
                if "Invalid symbol" in error_message or "API limit" in error_message:
                    print(f"CRITICAL: Finnhub symbol {finnhub_symbol} may be incorrect or API key is invalid/rate-limited.")

        except requests.RequestException as e:
            print(f"Error fetching Finnhub data for {symbol}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {symbol}: {e}")

        # Rate limit compliance: Finnhub free tier is 30 calls/min. We use 2 seconds to be safe.
        if i < len(SYMBOLS_TO_FETCH) - 1:
            print("Waiting 2 seconds for Finnhub rate limit...")
            time.sleep(2)

    # Save the combined data files
    save_json(market_data_history, "market_data_history.json")
    save_json(money_fund_data, "money_fund_data.json")


# --- Main Execution ---

if __name__ == "__main__":
    print("Starting data synchronization script...")
    
    # 1. Fetch HIBOR rates (Daily)
    fetch_hibor_rates()
    
    # 2. Fetch Fear & Greed Index
    fetch_fear_greed_index()
    
    # 3. Fetch Market Data (Indices, ETFs, Money Funds) using Finnhub
    fetch_market_data()
    
    print("Data synchronization complete.")
