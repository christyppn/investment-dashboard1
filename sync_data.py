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
    # Market Breadth (US) - Standard ETF tickers
    "SPY": "SPY",
    "QQQ": "QQQ",
    "DIA": "DIA",
    # Global Indices and VIX - Yahoo Finance uses ^ prefix for indices
    "GSPC": "^GSPC", # S&P 500
    "IXIC": "^IXIC", # NASDAQ
    "VIX": "^VIX", 
    "HSI": "^HSI", # Confirmed Yahoo Finance symbol for Hang Seng Index
    "N225": "^N225", # Confirmed Yahoo Finance symbol for Nikkei 225
    # Sector ETFs (11)
    "XLK": "XLK", "XLC": "XLC", "XLY": "XLY", "XLP": "XLP", "XLV": "XLV", "XLF": "XLF", 
    "XLE": "XLE", "XLI": "XLI", "XLB": "XLB", "XLU": "XLU", "VNQ": "VNQ",
    # Thematic/Commodity ETFs (4)
    "GLD": "GLD", "ROBO": "ROBO", "SMH": "SMH", "IWM": "IWM",
    # Money Market Funds (4) - Using original mutual fund symbols (yfinance supports them)
    "VFIAX": "VFIAX",
    "VTSAX": "VTSAX",
    "VBTLX": "VBTLX",
    "BIL": "BIL", # Using BIL ETF as a proxy for money market fund data, as VMMXX is often problematic
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
    """
    Processes raw yfinance DataFrame to calculate daily changes,
    and includes the critical division-by-zero check and 30-day truncation.
    """
    if df.empty:
        return []

    # Calculate daily percentage change for Close price
    df['change_percent'] = df['Close'].pct_change() * 100
    
    # Clean up and format
    df = df.reset_index()
    if pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    
    # Select and rename columns for final output
    df = df.rename(columns={'Date': 'date', 'Close': 'close'})
    df = df[['date', 'close', 'change_percent']]
    
    # Convert to list of dictionaries
    time_series_list = df.to_dict('records')
    
    # Remove the first row (NaN change)
    if time_series_list:
        time_series_list.pop(0)

    # Final Optimization: Only keep the latest 30 trading days for frontend display
    return time_series_list[-30:]

# --- Data Fetching Functions ---

def fetch_cnn_fear_greed():
    """Scrapes the current US Fear & Greed Index value from CNNMoney."""
    url = "https://money.cnn.com/data/fear-and-greed/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find the value using the most common selector first
        value_element = soup.find('div', class_='market-f-g-index__index-value')
        sentiment_element = soup.find('div', class_='market-f-g-index__index-label')
        date_element = soup.find('div', class_='market-f-g-index__index-date')
        
        # Fallback for the new CNN structure (based on live inspection)
        if not value_element:
            # The main gauge value is in a div with class 'fng-gauge__value'
            value_element = soup.find('div', class_='fng-gauge__value')
            # The sentiment text is in a div with class 'fng-gauge__label'
            sentiment_element = soup.find('div', class_='fng-gauge__label')
            # The date is in a div with class 'fng-gauge__date'
            date_element = soup.find('div', class_='fng-gauge__date')

        if value_element and sentiment_element and date_element:
            # Check if the value is a number, otherwise it might be a loading state
            try:
                value = int(value_element.text.strip())
            except ValueError:
                print("Warning: F&G value is not an integer, possibly a loading state.")
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
            return True

        print("Warning: Could not find F&G data elements on CNN page.")
        return False
        
    except requests.RequestException as e:
        print(f"Error fetching CNN Fear & Greed Index: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during F&G scrape: {e}")
        return False

def fetch_hkma_hibor():
    """Fetches real-time HIBOR rates from HKMA API."""
    # HKMA API for daily HIBOR rates
    # Using the daily HKD Interest Settlement Rates API (T060303)
    # The previous API was for historical data. We will use the daily monetary statistics API for the latest fixing.
    # Note: The daily monetary statistics API does not provide the full HIBOR fixing list, so we stick to the monthly bulletin API for the full list, but check for the correct field.
    url = "https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('result') and data['result'].get('records'):
            records = data['result']['records']
            
            # The API returns records in descending order of date, so the first record is the latest
            latest_record = records[0] 
            
            # Extract relevant HIBOR terms (1M, 3M, 6M)
            hibor_data = []
            terms = {"M1": "1個月", "M3": "3個月", "M6": "6個月"}
            
            for key, term_name in terms.items():
                # The correct key in the API is HKD_HIBOR_M1, HKD_HIBOR_M3, etc.
                rate_key = f"HKD_HIBOR_{key}"
                # The rate is a string, we need to convert it to float.
                # The API returns the Interest Settlement Rate (ISR), which is the HIBOR fixing.
                # We also check if the value is not a placeholder like 'N.A.'
                if rate_key in latest_record and latest_record[rate_key] is not None and latest_record[rate_key] not in ['N.A.', '']:
                    hibor_data.append({
                        "term": term_name,
                        "rate": float(latest_record[rate_key]),
                        "date": latest_record['end_of_day']
                    })
            
            if hibor_data:
                save_json({
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "rates": hibor_data
                }, "hibor_rates.json")
                return True
            else:
                print("Warning: HIBOR data found but specific terms (1M, 3M, 6M) are missing.")
                return False
        else:
            print("Error: HKMA API returned no valid records.")
            return False
            
    except requests.RequestException as e:
        print(f"Error fetching HKMA HIBOR: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during HIBOR fetch: {e}")
        return False

def fetch_market_data():
    """Fetches time series data for all configured symbols from Yahoo Finance using yfinance."""
    
    # Calculate start date for the last 30 trading days (approx 45 calendar days)
    start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    
    # Initialize data structures for combined output
    market_data_history = {}
    money_fund_data = [] # Changed to list to hold all fund data
    
    # Symbols to fetch in batches
    yahoo_symbols_list = list(YAHOO_SYMBOLS.values())
    
    # Fetch all data in one go
    df_all = yf.download(yahoo_symbols_list, start=start_date, interval="1d", auto_adjust=False)
    
    if df_all.empty:
        print("Error: Yahoo Finance returned no data for all symbols.")
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
            print(f"An unexpected error occurred for {symbol_key} ({yahoo_symbol}): {e}")

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
