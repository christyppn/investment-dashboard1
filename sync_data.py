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
    "VMMXX": "VMMXX", # If this fails, it means Yahoo Finance has temporarily stopped providing data for this specific fund.
}

# List of symbols to fetch (keys from the mapping)
SYMBOLS_TO_FETCH = list(YAHOO_SYMBOLS.keys())

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# --- Helper Functions ---

def save_json(data, filename):
    """Saves data to a JSON file in the data directory."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Successfully saved data to {path}")

def process_yahoo_data(symbol, df):
    """
    Processes raw yfinance DataFrame to calculate daily changes,
    and includes the critical division-by-zero check and 30-day truncation.
    """
    if df.empty:
        print(f"Warning: No valid Yahoo Finance data found for {symbol}")
        return []

    # Calculate daily percentage change for Close price
    df['change_percent'] = df['Close'].pct_change() * 100
    
    # Calculate daily percentage change for Volume
    # Handle cases where Volume is 0 (e.g., for some indices)
    df['Volume_shifted'] = df['Volume'].shift(1).replace(0, pd.NA)
    df['volume_change_percent'] = (df['Volume'] - df['Volume'].shift(1)) / df['Volume_shifted'] * 100
    df['volume_change_percent'] = df['volume_change_percent'].fillna(0).round(2)
    
    # Clean up and format
    df = df.reset_index()
    # Handle both datetime and object types for Date column
    if pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
    
    # Select and rename columns for final output
    df = df.rename(columns={'Date': 'date', 'Close': 'close', 'Volume': 'volume'})
    df = df[['date', 'close', 'volume', 'change_percent', 'volume_change_percent']]
    
    # Convert to list of dictionaries
    time_series_list = df.to_dict('records')
    
    # Remove the first row (NaN change)
    if time_series_list:
        time_series_list.pop(0)

    # Final Optimization: Only keep the latest 30 trading days for frontend display
    return time_series_list[-30:]

# --- Data Fetching Functions ---

def fetch_hibor_rates():
    """
    Generates static HIBOR data as a final fallback due to API/Scraping instability.
    Uses the latest rates manually extracted from HKAB website.
    """
    print("Generating static HIBOR rates as a final fallback...")
    
    # Data manually extracted from HKAB website on 2025-11-17
    current_time = datetime.now().isoformat()
    hibor_data = [
        {
            "id": "1M",
            "term": "1M",
            "rate": 3.00429, # Corrected rate
            "timestamp": current_time
        },
        {
            "id": "3M",
            "term": "3M",
            "rate": 3.43476, # Corrected rate
            "timestamp": current_time
        },
        {
            "id": "6M",
            "term": "6M",
            "rate": 3.41250, # Corrected rate
            "timestamp": current_time
        }
    ]
    
    save_json(hibor_data, "hibor_rates.json")
    print("Successfully generated static HIBOR rates.")


def fetch_fear_greed_index():
    """Fetches Fear & Greed Index from alternative.me API."""
    print("Fetching Fear & Greed Index...")
    url = "https://api.alternative.me/fng/?limit=30"
    
    try:
        response = requests.get(url, timeout=10)
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
    except Exception as e:
        print(f"An unexpected error occurred during F&G fetch: {e}")


def fetch_market_data():
    """Fetches time series data for all configured symbols from Yahoo Finance using yfinance."""
    
    # Calculate start date for the last 30 trading days (approx 45 calendar days)
    start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    
    # Initialize data structures for combined output
    market_data_history = {}
    money_fund_data = {}

    for i, symbol in enumerate(SYMBOLS_TO_FETCH):
        yahoo_symbol = YAHOO_SYMBOLS[symbol]
        print(f"Fetching data for {symbol} ({yahoo_symbol}) ({i+1}/{len(SYMBOLS_TO_FETCH)})...")
        
        try:
            # Download data from Yahoo Finance
            ticker = yf.Ticker(yahoo_symbol)
            # Use auto_adjust=False to get raw prices, which is better for historical analysis
            df = ticker.history(start=start_date, interval="1d", auto_adjust=False)
            
            if not df.empty:
                # Process and truncate the data
                processed_data = process_yahoo_data(symbol, df)
                
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
                print(f"Warning: Yahoo Finance returned no data for {symbol} ({yahoo_symbol}).")

        except Exception as e:
            print(f"An unexpected error occurred for {symbol} ({yahoo_symbol}): {e}")

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
    
    # 3. Fetch Market Data (Indices, ETFs, Money Funds) using Yahoo Finance (yfinance)
    fetch_market_data()
    
    print("Data synchronization complete.")
