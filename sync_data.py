import requests
import json
import os
import time
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from bs4 import BeautifulSoup

# --- Configuration ---
DATA_DIR = "data"
LOG_FILE = "sync_log.txt"

# Yahoo Finance Symbols (Confirmed symbols for all required data points)
YAHOO_SYMBOLS = {
    # ... (YAHOO_SYMBOLS definition remains the same) ...
    "SPY": "SPY", "QQQ": "QQQ", "DIA": "DIA", "GSPC": "^GSPC", "IXIC": "^IXIC", "VIX": "^VIX", 
    "HSI": "^HSI", "N225": "^N225", "XLK": "XLK", "XLC": "XLC", "XLY": "XLY", "XLP": "XLP", 
    "XLV": "XLV", "XLF": "XLF", "XLE": "XLE", "XLI": "XLI", "XLB": "XLB", "XLU": "XLU", 
    "VNQ": "VNQ", "GLD": "GLD", "ROBO": "ROBO", "SMH": "SMH", "IWM": "IWM",
    "VFIAX": "VFIAX", "VTSAX": "VTSAX", "VBTLX": "VBTLX", "BIL": "BIL",
}

# List of symbols to fetch (keys from the mapping)
SYMBOLS_TO_FETCH = list(YAHOO_SYMBOLS.keys())

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# --- Logging Function ---
def log_message(message):
    """Writes a timestamped message to the log file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_message = f"[{timestamp}] {message}\n"
    with open(os.path.join(DATA_DIR, LOG_FILE), 'a', encoding='utf-8') as f:
        f.write(full_message)

# --- Helper Functions ---
def save_json(data, filename):
    """Saves data to a JSON file in the data directory."""
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_message(f"SUCCESS: Saved {filename}")
    except Exception as e:
        log_message(f"ERROR: Failed to save {filename}: {e}")

def process_yahoo_data(symbol, df):
    # ... (Function body remains the same) ...
    if df.empty: return []
    df['change_percent'] = df['Close'].pct_change() * 100
    df = df.reset_index()
    if pd.api.types.is_datetime64_any_dtype(df['Date']): df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    df = df.rename(columns={'Date': 'date', 'Close': 'close'})
    df = df[['date', 'close', 'change_percent']]
    time_series_list = df.to_dict('records')
    if time_series_list: time_series_list.pop(0)
    return time_series_list[-30:]

# --- Data Fetching Functions ---

def fetch_cnn_fear_greed():
    """Scrapes the current US Fear & Greed Index value from CNNMoney."""
    log_message("Attempting to fetch CNN Fear & Greed Index...")
    url = "https://money.cnn.com/data/fear-and-greed/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10 )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find the value using the most common selector first
        value_element = soup.find('div', class_='market-f-g-index__index-value')
        sentiment_element = soup.find('div', class_='market-f-g-index__index-label')
        date_element = soup.find('div', class_='market-f-g-index__index-date')
        
        # Fallback for the new CNN structure
        if not value_element:
            value_element = soup.find('div', class_='fng-gauge__value')
            sentiment_element = soup.find('div', class_='fng-gauge__label')
            date_element = soup.find('div', class_='fng-gauge__date')

        if value_element and sentiment_element and date_element:
            try:
                value = int(value_element.text.strip())
            except ValueError:
                log_message(f"WARNING: F&G value is not an integer: {value_element.text.strip()}")
                return False
            
            sentiment = sentiment_element.text.strip()
            timestamp = date_element.text.strip().replace("Last updated ", "")
            
            data = {
                "timestamp": timestamp,
                "value": value,
                "sentiment": sentiment,
                "source": "CNNMoney (US)"
            }
            save_json(data, "fear_greed_index.json")
            log_message(f"SUCCESS: F&G Index fetched: {value} ({sentiment})")
            return True

        log_message("WARNING: Could not find F&G data elements on CNN page.")
        return False
        
    except requests.RequestException as e:
        log_message(f"ERROR: Request failed for CNN F&G: {e}")
        return False
    except Exception as e:
        log_message(f"FATAL ERROR: Unexpected error during F&G scrape: {e}")
        return False

def fetch_hkma_hibor():
    """Fetches real-time HIBOR rates from HKMA API."""
    log_message("Attempting to fetch HKMA HIBOR rates...")
    url = "https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily"
    
    try:
        response = requests.get(url, timeout=10 )
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('result') and data['result'].get('records'):
            records = data['result']['records']
            latest_record = records[0] 
            
            hibor_data = []
            terms = {"M1": "1個月", "M3": "3個月", "M6": "6個月"}
            
            for key, term_name in terms.items():
                rate_key = f"HKD_HIBOR_{key}"
                # Check for valid rate and not a placeholder
                if rate_key in latest_record and latest_record[rate_key] is not None and latest_record[rate_key] not in ['N.A.', '']:
                    try:
                        hibor_data.append({
                            "term": term_name,
                            "rate": float(latest_record[rate_key]),
                            "date": latest_record['end_of_day']
                        })
                    except ValueError:
                        log_message(f"WARNING: Could not convert HIBOR rate {latest_record[rate_key]} to float for {term_name}.")
            
            # Manually add Overnight rate
            if 'OVERNIGHT' in latest_record and latest_record['OVERNIGHT'] is not None and latest_record['OVERNIGHT'] not in ['N.A.', '']:
                try:
                    hibor_data.insert(0, {
                        "term": "隔夜",
                        "rate": float(latest_record['OVERNIGHT']),
                        "date": latest_record['end_of_day']
                    })
                except ValueError:
                    log_message(f"WARNING: Could not convert Overnight rate {latest_record['OVERNIGHT']} to float.")
            
            if hibor_data:
                save_json({
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "rates": hibor_data
                }, "hibor_rates.json")
                log_message(f"SUCCESS: HIBOR rates fetched for {len(hibor_data)} terms.")
                return True
            else:
                log_message("WARNING: HIBOR data found but specific terms (1M, 3M, 6M) are missing or invalid.")
                return False
        else:
            log_message("ERROR: HKMA API returned no valid records.")
            return False
            
    except requests.RequestException as e:
        log_message(f"ERROR: Request failed for HKMA HIBOR: {e}")
        return False
    except Exception as e:
        log_message(f"FATAL ERROR: Unexpected error during HIBOR fetch: {e}")
        return False

def fetch_market_data():
    # ... (Function body remains the same) ...
    log_message("Attempting to fetch Yahoo Finance market data...")
    start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    market_data_history = {}
    money_fund_data = []
    yahoo_symbols_list = list(YAHOO_SYMBOLS.values())
    
    try:
        df_all = yf.download(yahoo_symbols_list, start=start_date, interval="1d", auto_adjust=False, progress=False)
    except Exception as e:
        log_message(f"ERROR: Yahoo Finance download failed: {e}")
        return

    if df_all.empty:
        log_message("ERROR: Yahoo Finance returned no data for all symbols.")
        return

    for symbol_key, yahoo_symbol in YAHOO_SYMBOLS.items():
        # ... (Processing logic remains the same) ...
        pass # Placeholder for brevity

    # Save the combined data files
    # ... (Saving logic remains the same) ...
    log_message("SUCCESS: Yahoo Finance market data processed and saved.")

def generate_dummy_data():
    # ... (Function body remains the same) ...
    log_message("Generating dummy data for AI Analysis, 13F, and Market Sentiment.")
    # ... (Saving logic remains the same) ...
    log_message("SUCCESS: Dummy data generated.")

# --- Main Execution ---

if __name__ == "__main__":
    # Clear previous log
    if os.path.exists(os.path.join(DATA_DIR, LOG_FILE)):
        os.remove(os.path.join(DATA_DIR, LOG_FILE))
    
    log_message("--- Starting data synchronization script ---")
    
    # 1. Generate Dummy Data (for files not fetched live)
    generate_dummy_data()
    
    # 2. Fetch US Fear & Greed Index (Scraping)
    fetch_cnn_fear_greed()
    
    # 3. Fetch HIBOR rates (HKMA API)
    fetch_hkma_hibor()
    
    # 4. Fetch Market Data (Indices, ETFs, Money Funds) using Yahoo Finance (yfinance)
    fetch_market_data()
    
    log_message("--- Data synchronization complete ---")
