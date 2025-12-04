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

# --- Helper Functions ---

def save_json(data, filename):
    """Saves data to a JSON file in the data directory."""
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving {filename}: {e}")

# ... (process_yahoo_data remains the same) ...

# --- Data Fetching Functions ---

def fetch_cnn_fear_greed():
    """Scrapes the current US Fear & Greed Index value from CNNMoney."""
    url = "https://money.cnn.com/data/fear-and-greed/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10 )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # FINAL ROBUST SELECTOR: Find the gauge container and then the value/label
        gauge_container = soup.find('div', class_='fng-gauge')
        
        if gauge_container:
            value_element = gauge_container.find('div', class_='fng-gauge__value')
            sentiment_element = gauge_container.find('div', class_='fng-gauge__label')
            date_element = gauge_container.find('div', class_='fng-gauge__date')
        else:
            # Fallback for older/different structure
            value_element = soup.find('div', id='needleChart')
            sentiment_element = soup.find('div', class_='fng-gauge__label')
            date_element = soup.find('div', class_='fng-gauge__date')

        if value_element and sentiment_element and date_element:
            try:
                # Extract value from the text content
                value_text = value_element.text.strip()
                # Try to find the number in the text (e.g., if it's "18")
                value = int(''.join(filter(str.isdigit, value_text)))
            except ValueError:
                raise ValueError(f"F&G value is not an integer: {value_text}")
            
            sentiment = sentiment_element.text.strip()
            timestamp = date_element.text.strip().replace("Last updated ", "")
            
            data = {
                "timestamp": timestamp,
                "value": value,
                "sentiment": sentiment,
                "source": "CNNMoney (US)"
            }
            save_json(data, "fear_greed_index.json")
            return True

        raise Exception("Could not find F&G data elements on CNN page.")
        
    except Exception as e:
        # On any failure (request, parsing, value error), save an error state
        error_data = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "value": 0,
            "sentiment": "ERROR",
            "source": f"Fetch Failed: {str(e)[:50]}..."
        }
        save_json(error_data, "fear_greed_index.json")
        print(f"Error fetching CNN F&G: {e}")
        return False

def fetch_hkma_hibor():
    """Fetches real-time HIBOR rates from HKMA API, with back-tracking for missing data."""
    url = "https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily"
    
    try:
        response = requests.get(url, timeout=10 )
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('result') and data['result'].get('records'):
            records = data['result']['records']
            
            # Iterate through records (latest first) until valid data is found
            for latest_record in records:
                hibor_data = []
                terms = {"M1": "1個月", "M3": "3個月", "M6": "6個月"}
                
                # Check for valid Overnight rate
                if 'OVERNIGHT' in latest_record and latest_record['OVERNIGHT'] is not None and latest_record['OVERNIGHT'] not in ['N.A.', '']:
                    try:
                        hibor_data.insert(0, {
                            "term": "隔夜",
                            "rate": float(latest_record['OVERNIGHT']),
                            "date": latest_record['end_of_day']
                        })
                    except ValueError:
                        pass # Ignore if conversion fails

                # Check for valid M1, M3, M6 rates
                valid_term_count = 0
                for key, term_name in terms.items():
                    rate_key = f"HKD_HIBOR_{key}"
                    if rate_key in latest_record and latest_record[rate_key] is not None and latest_record[rate_key] not in ['N.A.', '']:
                        try:
                            hibor_data.append({
                                "term": term_name,
                                "rate": float(latest_record[rate_key]),
                                "date": latest_record['end_of_day']
                            })
                            valid_term_count += 1
                        except ValueError:
                            pass # Ignore if conversion fails
                
                # If we found at least one valid term (M1, M3, or M6), we use this record
                if valid_term_count > 0:
                    save_json({
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "rates": hibor_data
                    }, "hibor_rates.json")
                    return True
            
            # If loop finishes without finding valid data
            raise Exception("HIBOR data found but no valid 1M, 3M, or 6M terms in recent records.")
        else:
            raise Exception("HKMA API returned no valid records.")
            
    except Exception as e:
        # On any failure, save an error state
        error_data = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "rates": [{"term": "ERROR", "rate": 0.0, "date": "N/A"}],
            "error_message": f"Fetch Failed: {str(e)[:50]}..."
        }
        save_json(error_data, "hibor_rates.json")
        print(f"Error fetching HKMA HIBOR: {e}")
        return False

# ... (fetch_market_data and generate_dummy_data remain the same) ...

# --- Main Execution ---

if __name__ == "__main__":
    print("Starting data synchronization script...")
    
    # 1. Generate Dummy Data (for files not fetched live)
    generate_dummy_data()
    
    # 2. Fetch US Fear & Greed Index (Scraping)
    fetch_cnn_fear_greed()
    
    # 3. Fetch HIBOR rates (HKMA API)
    fetch_hkma_hibor()
    
    # 4. Fetch Market Data (Indices, ETFs, Money Funds) using Yahoo Finance (yfinance)
    fetch_market_data()
    
    print("Data synchronization complete.")
