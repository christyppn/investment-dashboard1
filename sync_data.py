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
    url = "https://money.cnn.com/data/fear-and-greed/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10 )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # FINAL ROBUST SELECTOR: Find the gauge container and then the value/label
        # Search for the main data container which holds the value and sentiment
        gauge_container = soup.find('div', class_='fng-gauge')
        
        if gauge_container:
            value_element = gauge_container.find('div', class_='fng-gauge__value')
            sentiment_element = gauge_container.find('div', class_='fng-gauge__label')
            date_element = gauge_container.find('div', class_='fng-gauge__date')
        else:
            # Fallback: Search for the data in the script tags (often a JSON blob)
            script_tags = soup.find_all('script')
            for script in script_tags:
                if 'var data' in script.text and 'Fear & Greed' in script.text:
                    # This is a complex fallback, let's stick to the simpler robust selector first
                    pass
            
            # If the simple robust selector failed, we need to try a different class name
            value_element = soup.find('div', class_='market-fng-gauge__value')
            sentiment_element = soup.find('div', class_='market-fng-gauge__label')
            date_element = soup.find('div', class_='market-fng-gauge__date')

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

def fetch_market_data():
    """Fetches time series data for all configured symbols from Yahoo Finance using yfinance."""
    # ... (Function body remains the same) ...
    start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    market_data_history = {}
    money_fund_data = []
    yahoo_symbols_list = list(YAHOO_SYMBOLS.values())
    
    try:
        # Suppress yfinance output
        df_all = yf.download(yahoo_symbols_list, start=start_date, interval="1d", auto_adjust=False, progress=False)
    except Exception as e:
        print(f"ERROR: Yahoo Finance download failed: {e}")
        return

    if df_all.empty:
        print("ERROR: Yahoo Finance returned no data for all symbols.")
        return

    for symbol_key, yahoo_symbol in YAHOO_SYMBOLS.items():
        try:
            # Extract the data for the specific symbol
            if isinstance(df_all['Close'], pd.DataFrame):
                df = df_all.loc[:, (slice(None), yahoo_symbol)].droplevel(1, axis=1)
            else:
                # Handle case where only one symbol was fetched (df_all is a Series)
                df = df_all
            
            if not df.empty:
                # Process and truncate the data
                processed_data = process_yahoo_data(symbol_key, df)
                
                # Separate data based on symbol type
                if symbol_key in ["VFIAX", "VTSAX", "VBTLX", "BIL"]:
                    # Money Fund Data: Only need the latest data point
                    if processed_data:
                        latest_data = processed_data[-1]
                        money_fund_data.append({
                            "symbol": symbol_key,
                            "latest_price": latest_data['close'],
                            "daily_change_percent": latest_data['change_percent'],
                            "date": latest_data['date']
                        })
                else:
                    # Market Breadth and Global Market Data: Need the 30-day history
                    # We need to add the full name for the chart legend
                    if processed_data:
                        # Add full name to the first element for chart legend
                        processed_data[0]['name'] = symbol_key 
                        market_data_history[symbol_key] = processed_data
            
        except Exception as e:
            print(f"ERROR: Unexpected error occurred for {symbol_key} ({yahoo_symbol}): {e}")

    # Save the combined data files
    save_json(market_data_history, "market_data_history.json")
    
    # Save money fund data
    save_json({
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "funds": money_fund_data
    }, "money_fund_data.json")

def generate_dummy_data():
    """Generates dummy data for files not covered by real-time fetching."""
    
    # 1. AI Analysis (Static for now)
    ai_analysis = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "sentiment": "Bullish",
        "analysis": "市場情緒持續樂觀，主要指數在科技股帶動下創下新高。建議關注半導體和人工智能相關領域的長期投資機會。"
    }
    save_json(ai_analysis, 'ai_analysis.json')
    
    # 2. 13F Data (Dummy)
    f13_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "holdings": [
            {"symbol": "AAPL", "value": 246.5, "change": -13.2},
            {"symbol": "BAC", "value": 54.8, "change": -5.6},
            {"symbol": "KO", "value": 26.4, "change": 0.0},
        ]
    }
    save_json(f13_data, '13f-data.json')
    
    # 3. Market Sentiment (Dummy for Consensus)
    market_sentiment = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "consensus": {
            "latest_sentiment": "中性偏多",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    save_json(market_sentiment, 'market_sentiment.json')

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
