import requests
import json
import os
import time
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from bs4 import BeautifulSoup
import random
import re
import logging

# --- Configuration ---
DATA_DIR = "data"
MAX_RETRIES = 3
RETRY_DELAY = 5 # seconds

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sync_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Yahoo Finance Symbols (Confirmed symbols for all required data points)
YAHOO_SYMBOLS = {
    # Market Breadth (US) - Standard ETF tickers
    "SPY": "SPY", "QQQ": "QQQ", "DIA": "DIA",
    # Global Indices and VIX
    "GSPC": "^GSPC", "IXIC": "^IXIC", "VIX": "^VIX", "HSI": "^HSI", "N225": "^N225",
    # Sector ETFs
    "XLK": "XLK", "XLC": "XLC", "XLY": "XLY", "XLP": "XLP", "XLV": "XLV", "XLF": "XLF",
    "XLE": "XLE", "XLI": "XLI", "XLB": "XLB", "XLU": "XLU", "VNQ": "VNQ",
    # Commodities/Thematic
    "GLD": "GLD", "ROBO": "ROBO", "SMH": "SMH", "IWM": "IWM",
    # Money Funds (for money_fund.js)
    "VFIAX": "VFIAX", "VTSAX": "VBTLX", "BIL": "BIL"
}

# --- Helper Functions ---

def _get_user_agent() -> str:
    """Get a random User-Agent strings to avoid being blocked by scraping targets."""
    user_agent_strings = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    return random.choice(user_agent_strings)

def save_json(data, filename):
    """Saves data to a JSON file in the data directory."""
    path = os.path.join(DATA_DIR, filename)
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Successfully saved data to {path}")
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")

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

def fetch_with_retry(url, headers=None, timeout=15):
    """Attempts to fetch a URL with a retry mechanism."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {url}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1)) # Exponential backoff
            else:
                logger.error(f"All {MAX_RETRIES} attempts failed for {url}.")
                raise

# --- Data Fetching Functions ---

def fetch_alternative_fng():
    """Fetches the Crypto Fear & Greed Index from Alternative.me API."""
    url = "https://api.alternative.me/fng/"
    error_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "value": 0,
        "sentiment": "ERROR",
        "source": "Fetch Failed: Alternative.me API error."
    }
    
    try:
        response = fetch_with_retry(url)
        data = response.json()
        
        if data and data.get('data') and len(data['data']) > 0:
            fng_data = data['data'][0]
            value = int(fng_data.get('value', 0))
            sentiment = fng_data.get('value_classification', 'ERROR')
            
            final_data = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "value": value,
                "sentiment": sentiment,
                "source": "Alternative.me (Crypto) API"
            }
            save_json(final_data, 'fear_greed_index.json')
            logger.info("Successfully fetched Fear & Greed Index from Alternative.me API.")
            return True
        
        error_data["source"] = "Fetch Failed: Alternative.me API returned no data."
        save_json(error_data, 'fear_greed_index.json')
        return False

    except Exception as e:
        error_data["source"] = f"Fetch Failed: Network or Parsing Error: {str(e)[:100]}..."
        save_json(error_data, 'fear_greed_index.json')
        logger.error(f"Failed to fetch F&G data: {e}")
        return False

def fetch_hkma_hibor():
    """Fetches HIBOR rates from HKMA API with corrected field names and backtracking."""
    url = "https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily"
    keys = ['ir_1m', 'ir_3m', 'ir_6m'] # Corrected keys based on raw JSON inspection
    
    error_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "rates": [{"term": "ERROR", "rate": 0.0, "date": "N/A"}],
        "error_message": "Fetch Failed: Network or API Error."
    }

    try:
        response = fetch_with_retry(url)
        data = response.json()
        
        if data.get('header', {}).get('success') != True or not data.get('result', {}).get('records'):
            error_data["error_message"] = f"Fetch Failed: HKMA API returned error or no records. Message: {data.get('header', {}).get('err_msg')}"
            save_json(error_data, "hibor_rates.json")
            logger.error(f"HKMA API returned error or no records: {error_data['error_message']}")
            return False

        records = data['result']['records']
        
        valid_rates = {}
        data_date = "N/A"
        
        for record in records:
            # Check if all required keys have valid, non-null values
            if all(record.get(key) is not None for key in keys):
                data_date = record['end_of_day']
                valid_rates = {
                    'Overnight': float(record.get('ir_overnight', 0.0)),
                    '1個月': float(record.get('ir_1m', 0.0)),
                    '3個月': float(record.get('ir_3m', 0.0)),
                    '6個月': float(record.get('ir_6m', 0.0)),
                }
                break

        if not valid_rates:
            error_data["error_message"] = "Fetch Failed: No valid HIBOR data found in recent records."
            save_json(error_data, "hibor_rates.json")
            logger.error("No valid HIBOR data found in recent records.")
            return False

        final_data = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data_date": data_date,
            "rates": [
                {"term": term, "rate": rate} for term, rate in valid_rates.items()
            ]
        }
        save_json(final_data, "hibor_rates.json")
        logger.info("Successfully fetched HIBOR rates.")
        return True
            
    except Exception as e:
        error_data["error_message"] = f"Fetch Failed: Network or API Error: {str(e)[:100]}..."
        save_json(error_data, "hibor_rates.json")
        logger.error(f"Failed to fetch HIBOR data: {e}")
        return False

def fetch_market_data():
    """Fetches market data (indices, ETFs, money funds) using yfinance."""
    start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    market_data_history = {}
    money_fund_data = []
    yahoo_symbols_list = list(YAHOO_SYMBOLS.values())
    
    try:
        df_all = yf.download(yahoo_symbols_list, start=start_date, interval="1d", auto_adjust=False, progress=False)
        if df_all.empty:
            logger.error("Yahoo Finance returned no data.")
            return False
    except Exception as e:
        logger.error(f"Error fetching from Yahoo Finance: {e}")
        return False

    for symbol_key, yahoo_symbol in YAHOO_SYMBOLS.items():
        try:
            if isinstance(df_all['Close'], pd.DataFrame):
                df = df_all.loc[:, (slice(None), yahoo_symbol)].droplevel(1, axis=1)
            else:
                df = df_all
            
            if not df.empty:
                processed_data = process_yahoo_data(symbol_key, df)
                if symbol_key in ["VFIAX", "VTSAX", "VBTLX", "BIL"]:
                    if processed_data:
                        latest_data = processed_data[-1]
                        money_fund_data.append({
                            "symbol": symbol_key,
                            "latest_price": latest_data['close'],
                            "daily_change_percent": latest_data['change_percent'],
                            "date": latest_data['date']
                        })
                else:
                    if processed_data:
                        processed_data[0]['name'] = symbol_key 
                        market_data_history[symbol_key] = processed_data
        except Exception as e:
            logger.error(f"Could not process data for {symbol_key}: {e}")

    save_json(market_data_history, "market_data_history.json")
    save_json({
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "funds": money_fund_data
    }, "money_fund_data.json")
    logger.info("Successfully fetched market data from Yahoo Finance.")
    return True

def generate_dummy_data():
    """Generates dummy data for files not covered by real-time fetching."""
    ai_analysis = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "sentiment": "Bullish",
        "analysis": "市場情緒持續樂觀，主要指數在科技股帶動下創下新高。建議關注半導體和人工智能相關領域的長期投資機會。",
        "rating": "Bullish"
    }
    save_json(ai_analysis, 'ai_analysis.json')
    
    f13_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "fund_name": "伯克希爾·哈撒韋 (BRK.B) 13F 持倉 (Q3 2025)",
        "total_value": 422.38,
        "cash_ratio": 167.68,
        "top_10_ratio": 85.2,
        "quarterly_change": -2.5,
        "holdings": [
            {"symbol": "AAPL", "value": 150.5, "change": 1.2},
            {"symbol": "BAC", "value": 54.8, "change": -5.6},
            {"symbol": "KO", "value": 26.4, "change": 0.0},
        ]
    }
    save_json(f13_data, '13f-data.json')
    
    market_sentiment = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "consensus": {
            "latest_sentiment": "中性偏多",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    save_json(market_sentiment, 'market_sentiment.json')
    logger.info("Successfully generated dummy data.")

# --- Main Execution ---

if __name__ == "__main__":
    logger.info("Starting data synchronization script...")
    generate_dummy_data()
    fetch_alternative_fng()
    fetch_hkma_hibor()
    fetch_market_data()
    logger.info("Data synchronization complete.")
