import requests
import json
import os
import time
from datetime import datetime, timedelta

# --- Configuration ---
# Alpha Vantage API Key is stored as a GitHub Secret (ALPHAVANTAGE_API_KEY)
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHAVANTAGE_API_KEY")
DATA_DIR = "data"

# List of symbols to fetch from Alpha Vantage
# Expanded to include major indices, sector ETFs, and thematic ETFs
SYMBOLS_TO_FETCH = [
    # Major Indices/Breadth
    "SPY", "QQQ", "DIA",
    # Sector ETFs (11)
    "XLK", "XLC", "XLY", "XLP", "XLV", "XLF", "XLE", "XLI", "XLB", "XLU", "VNQ", # VNQ for Real Estate
    # Thematic/Commodity ETFs (4)
    "GLD", "ROBO", "SMH", "IWM",
    # Money Market Funds (4)
    "VFIAX", "VTSAX", "VBTLX", "VMMXX",
]

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# --- Helper Functions ---

def save_json(data, filename):
    """Saves data to a JSON file in the data directory."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Successfully saved data to {path}")

def get_previous_day_data(time_series_list, current_date):
    """Finds the data for the trading day immediately preceding the current_date."""
    # Sort by date descending
    sorted_list = sorted(time_series_list, key=lambda x: x['date'], reverse=True)
    
    # Find the first entry whose date is less than the current_date
    for entry in sorted_list:
        if entry['date'] < current_date:
            return entry
    return None

def process_time_series_data(symbol, time_series_data):
    """
    Processes raw Alpha Vantage time series data to calculate daily changes,
    and includes the critical division-by-zero check and 30-day truncation.
    """
    if not time_series_data:
        print(f"Warning: No time series data found for {symbol}")
        return []

    # Convert raw data into a list of dictionaries for easier processing
    time_series_list = []
    for date_str, data in time_series_data.items():
        try:
            # Alpha Vantage keys are prefixed with numbers, e.g., '1. open'
            close_price = float(data['4. close'])
            volume = int(data['6. volume'])
            
            time_series_list.append({
                'date': date_str,
                'close': close_price,
                'volume': volume,
                'change_percent': 0.0,
                'volume_change_percent': 0.0,
            })
        except (ValueError, KeyError) as e:
            print(f"Error processing data for {symbol} on {date_str}: {e}")
            continue

    # Sort the list by date ascending to ensure correct calculation of previous day
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
            # If previous close is 0 or None, change is undefined or 0
            current['change_percent'] = 0.0

        # --- Volume Change Calculation with Division-by-Zero Check ---
        latest_volume = current['volume']
        previous_volume = previous['volume']
        
        if previous_volume is not None and previous_volume != 0:
            volume_change = ((latest_volume - previous_volume) / previous_volume) * 100
            current['volume_change_percent'] = round(volume_change, 2)
        else:
            # If previous volume is 0 or None, volume change is undefined or 0
            current['volume_change_percent'] = 0.0

    # Final Optimization: Only keep the latest 30 trading days for frontend display
    # This resolves the chart overcrowding issue.
    return time_series_list[-30:]

# --- Data Fetching Functions ---

def fetch_hibor_rates():
    """Fetches HIBOR rates from HKMA API."""
    print("Fetching HIBOR rates...")
    url = "https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/er-ir-hkr-m"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('result') and data['result'].get('records'):
            # Get the latest record
            latest_record = data['result']['records'][0]
            
            # Corrected keys based on HKMA API structure
            hibor_data = {
                "date": latest_record.get('end_of_month'),
                "ir_1m": latest_record.get('ir_1m'),
                "ir_3m": latest_record.get('ir_3m'),
                "ir_6m": latest_record.get('ir_6m'),
            }
            save_json(hibor_data, "hibor_rates.json")
        else:
            print("Error: HKMA API returned no records.")
            
    except requests.RequestException as e:
        print(f"Error fetching HIBOR rates: {e}")

def fetch_fear_greed_index():
    """Fetches Fear & Greed Index from alternative.me API."""
    print("Fetching Fear & Greed Index...")
    url = "https://api.alternative.me/fng/?limit=30" # Limit to 30 days
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('data'):
            # Data is already sorted by date descending, reverse it for the frontend chart
            history_data = sorted(data['data'], key=lambda x: int(x['timestamp']))
            
            # Format the data for the frontend
            formatted_data = []
            for record in history_data:
                # Convert timestamp to YYYY-MM-DD format
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

def fetch_alpha_vantage_data():
    """Fetches time series data for all configured symbols from Alpha Vantage."""
    if not ALPHA_VANTAGE_API_KEY:
        print("Error: ALPHAVANTAGE_API_KEY environment variable not set.")
        return

    base_url = "https://www.alphavantage.co/query"
    
    # Initialize data structures for combined output
    market_data_history = {}
    money_fund_data = {}

    for i, symbol in enumerate(SYMBOLS_TO_FETCH):
        print(f"Fetching data for {symbol} ({i+1}/{len(SYMBOLS_TO_FETCH)})...")
        
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "full", # Request full history to ensure 30 trading days are available
            "apikey": ALPHA_VANTAGE_API_KEY
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Check for API call error (e.g., invalid key, rate limit)
            if "Error Message" in data:
                print(f"Alpha Vantage Error for {symbol}: {data['Error Message']}")
                continue
            if "Note" in data:
                print(f"Alpha Vantage Note for {symbol}: {data['Note']}")
                # Continue, as rate limit note might still contain some data

            time_series_key = "Time Series (Daily)"
            if time_series_key in data:
                raw_time_series = data[time_series_key]
                
                # Process and truncate the data
                processed_data = process_time_series_data(symbol, raw_time_series)
                
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
                print(f"Warning: Time Series data not found in response for {symbol}.")

        except requests.RequestException as e:
            print(f"Error fetching Alpha Vantage data for {symbol}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {symbol}: {e}")

        # Rate limit compliance: 5 calls per minute (12 seconds per call)
        # We use 15 seconds to be safe.
        if i < len(SYMBOLS_TO_FETCH) - 1:
            print("Waiting 15 seconds for Alpha Vantage rate limit...")
            time.sleep(15)

    # Save the combined data files
    save_json(market_data_history, "market_data_history.json")
    save_json(money_fund_data, "money_fund_data.json")


# --- Main Execution ---

if __name__ == "__main__":
    print("Starting data synchronization script...")
    
    # 1. Fetch HIBOR rates
    fetch_hibor_rates()
    
    # 2. Fetch Fear & Greed Index
    fetch_fear_greed_index()
    
    # 3. Fetch Alpha Vantage data (Indices, ETFs, Money Funds)
    fetch_alpha_vantage_data()
    
    print("Data synchronization complete.")

