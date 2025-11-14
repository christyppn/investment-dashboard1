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

def fetch_hibor_from_hkab():
    """
    Fetches HIBOR rates by scraping the HKAB website as a fallback.
    """
    print("Attempting to scrape HIBOR rates from HKAB website...")
    url = "https://www.hkab.org.hk/tc/rates/hibor"
    target_terms = {"1個月": "1M", "3個月": "3M", "6個月": "6M"}
    hibor_data = []
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Find the table containing the HIBOR rates. Based on inspection, it's a table with class 'table'
        # The structure is: table -> tbody -> tr (rows) -> td (cells)
        # We look for the table that contains the HIBOR data.
        
        # A more robust way is to find the table header that contains "到期日" (Maturity)
        table = soup.find('table')
        
        if not table:
            print("Warning: Could not find the main HIBOR table on HKAB page.")
            return []

        # Find the header row to determine column indices
        header_row = table.find('thead').find('tr') if table.find('thead') else table.find('tr')
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # Find the column index for the date (到期日) and the target terms
        date_col_index = -1
        term_col_indices = {}
        
        for i, header in enumerate(headers):
            if "到期日" in header:
                date_col_index = i
            elif header in target_terms:
                term_col_indices[header] = i

        if date_col_index == -1 or not term_col_indices:
            print("Warning: Could not find required columns (到期日, 1個月, 3個月, 6個月) in the table.")
            return []

        # Find the data rows (latest data is usually the first row in the tbody)
        data_rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]
        
        if not data_rows:
            print("Warning: Could not find any data rows in the HIBOR table.")
            return []

        # We only need the latest data, which is the first row
        latest_row = data_rows[0]
        cells = latest_row.find_all('td')
        
        if len(cells) <= max(term_col_indices.values()):
            print("Warning: Data row has too few columns.")
            return []

        # Extract the date (timestamp)
        date_str = cells[date_col_index].get_text(strip=True)
        # Format the date to ISO-like string for consistency
        try:
            # Assuming date_str is in YYYY-MM-DD format or similar
            timestamp = datetime.strptime(date_str, '%Y-%m-%d').isoformat()
        except ValueError:
            # Fallback if date format is different (e.g., YYYY/MM/DD)
            try:
                timestamp = datetime.strptime(date_str, '%Y/%m/%d').isoformat()
            except ValueError:
                timestamp = datetime.now().isoformat()
        
        # Extract the rates
        for term_cn, term_en in target_terms.items():
            col_index = term_col_indices.get(term_cn)
            if col_index is not None:
                rate_str = cells[col_index].get_text(strip=True)
                try:
                    rate = float(rate_str)
                    hibor_data.append({
                        "id": timestamp,
                        "term": term_en,
                        "rate": rate,
                        "timestamp": timestamp
                    })
                except ValueError:
                    print(f"Warning: Could not parse rate for {term_cn}: {rate_str}")

        if hibor_data:
            print(f"Successfully scraped {len(hibor_data)} HIBOR rates from HKAB.")
            return hibor_data
        else:
            print("Warning: Scraped data was empty or invalid.")
            return []

    except requests.RequestException as e:
        print(f"Error scraping HIBOR rates from HKAB: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during HKAB scrape: {e}")
        return []


def fetch_hibor_rates():
    """
    Fetches HIBOR rates, trying HKMA API first, then falling back to HKAB scrape.
    """
    print("Fetching HIBOR rates...")
    hibor_data = []
    
    # 1. Try HKMA API (Original method)
    hkma_url = "https://api.hkma.gov.hk/public/market-data-and-statistics/market-data/interest-rate/hk-interbank-interest-rates-daily"
    target_terms = ["1M", "3M", "6M"]
    
    try:
        print("Trying HKMA API...")
        response = requests.get(hkma_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        records = data.get('result', {}).get('records', [])
        
        latest_rates = {}
        for record in records:
            term = record.get('term')
            if term in target_terms and term not in latest_rates:
                latest_rates[term] = {
                    "id": record.get('end_of_day_dt'),
                    "term": term,
                    "rate": record.get('rate'),
                    "timestamp": record.get('end_of_day_dt')
                }
        
        hibor_data = list(latest_rates.values())
        
        if hibor_data:
            print(f"Successfully fetched {len(hibor_data)} HIBOR rates from HKMA.")
        else:
            print("HKMA API returned no valid records. Falling back to HKAB scrape.")

    except requests.RequestException as e:
        print(f"Error fetching HIBOR rates from HKMA: {e}. Falling back to HKAB scrape.")
    except Exception as e:
        print(f"An unexpected error occurred during HKMA fetch: {e}. Falling back to HKAB scrape.")

    # 2. Fallback to HKAB Scrape
    if not hibor_data:
        hibor_data = fetch_hibor_from_hkab()

    # 3. Save the result
    if hibor_data:
        save_json(hibor_data, "hibor_rates.json")
    else:
        save_json([], "hibor_rates.json")
        print("Warning: Failed to fetch HIBOR rates from both sources.")


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
