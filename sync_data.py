# sync_data.py - Final Corrected Version

import yfinance as yf
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import time
import os

# --- Configuration ---
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Symbols to fetch
# Core Indices: SPY, QQQ, DIA, VIX, Global Markets (HSI, N225, GSPC, IXIC)
# Sector ETFs: XLK, XLC, XLY, XLP, XLV, XLF, XLE, XLI, XLB, XLU, VNQ
# Thematic/Other: GLD, ROBO, SMH, IWM
# Money Market: VFIAX, VMMXX, SWVXX, FXNAX (Note: yfinance may not support all mutual funds)
SYMBOLS = [
    "SPY", "QQQ", "DIA", "VIX", "HSI", "N225", "GSPC", "IXIC", "BTC-USD",
    "XLK", "XLC", "XLY", "XLP", "XLV", "XLF", "XLE", "XLI", "XLB", "XLU", "VNQ",
    "GLD", "ROBO", "SMH", "IWM",
    "VFIAX", "VMMXX", "SWVXX", "FXNAX"
]

# --- Helper Functions ---

def save_json(data, filename):
    """Saves data to a JSON file in the data directory."""
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved {filename}")
    except Exception as e:
        print(f"Error saving {filename}: {e}")

def get_market_data(symbols):
    """Fetches historical data for a list of symbols using yfinance."""
    print(f"Fetching data for {len(symbols)} symbols...")
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365 * 3)).strftime('%Y-%m-%d') # 3 years of data

    data = yf.download(symbols, start=start_date, end=end_date, interval="1d", group_by='ticker')
    
    market_data_history = {}
    for symbol in symbols:
        try:
            # Handle single ticker download which returns a simple DataFrame
            if len(symbols) == 1:
                df = data
            else:
                df = data[symbol]
            
            # Clean up columns and convert to list of dicts
            df = df.dropna(subset=['Close'])
            df.index = df.index.strftime('%Y-%m-%d')
            
            # Calculate daily change percentage
            df['Change_Pct'] = df['Close'].pct_change() * 100
            
            # Prepare data structure for JSON
            history = df[['Open', 'High', 'Low', 'Close', 'Volume', 'Change_Pct']].reset_index().rename(columns={'index': 'Date'})
            market_data_history[symbol] = history.to_dict('records')
            
        except KeyError:
            print(f"Warning: Could not find data for symbol {symbol}. Skipping.")
        except Exception as e:
            print(f"Error processing data for {symbol}: {e}")

    return market_data_history

def generate_hibor_rates():
    """Generates static HIBOR rates (as HKMA API is unreliable)."""
    print("Generating static HIBOR rates...")
    today = datetime.now().strftime('%Y-%m-%d')
    hibor_data = {
        "date": today,
        "rates": {
            "1M": 4.85,  # Example static rate
            "3M": 5.05,
            "6M": 5.20
        },
        "source": "Static data due to unreliable HKMA API."
    }
    save_json(hibor_data, "hibor_rates.json")

def get_fear_greed_index():
    """Fetches Fear & Greed Index from alternative.me."""
    print("Fetching Fear & Greed Index...")
    try:
        response = requests.get("https://api.alternative.me/fng/?limit=1" )
        response.raise_for_status()
        data = response.json()
        
        if data and data.get('data'):
            fng_data = data['data'][0]
            fng_index = {
                "value": int(fng_data['value']),
                "classification": fng_data['value_classification'],
                "timestamp": int(fng_data['timestamp'])
            }
            save_json(fng_index, "fear_greed_index.json")
            return fng_index
        else:
            print("Fear & Greed Index API returned no data.")
            return None
    except Exception as e:
        print(f"Error fetching Fear & Greed Index: {e}")
        return None

def generate_ai_analysis(market_data):
    """Generates rule-based AI analysis and 7-day prediction."""
    print("Generating rule-based AI analysis...")
    
    # Simple rule: Check SPY's last 5 days close price trend
    spy_data = market_data.get("SPY", [])
    if not spy_data:
        analysis = "Market data (SPY) is unavailable for analysis."
        prediction = "Neutral"
    else:
        df = pd.DataFrame(spy_data).set_index('Date')
        last_5_closes = df['Close'].tail(5)
        
        # Trend analysis
        if last_5_closes.iloc[-1] > last_5_closes.iloc[0]:
            trend = "Bullish"
            analysis = "The S&P 500 (SPY) has shown a positive trend over the last five trading days, suggesting strong short-term momentum."
            prediction = "Slightly Bullish"
        elif last_5_closes.iloc[-1] < last_5_closes.iloc[0]:
            trend = "Bearish"
            analysis = "The S&P 500 (SPY) has declined over the last five trading days, indicating potential short-term weakness."
            prediction = "Slightly Bearish"
        else:
            trend = "Neutral"
            analysis = "The S&P 500 (SPY) has been flat over the last five trading days, suggesting a consolidation phase."
            prediction = "Neutral"

    ai_data = {
        "date": datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        "model": "Rule-Based Analysis Engine",
        "analysis": analysis,
        "prediction_7_day": prediction,
        "confidence": "Medium (Rule-Based)"
    }
    save_json(ai_data, "ai_analysis.json")

def generate_market_breadth(market_data):
    """Generates a simple market breadth indicator based on the last day's change."""
    print("Generating market breadth data...")
    
    if not market_data:
        breadth_data = {"date": datetime.now().strftime('%Y-%m-%d'), "advancers": 0, "decliners": 0, "neutral": 0}
        save_json(breadth_data, "market_breadth.json")
        return

    advancers = 0
    decliners = 0
    neutral = 0
    
    # Use a subset of symbols for breadth calculation (e.g., all ETFs and major indices)
    breadth_symbols = [s for s in SYMBOLS if s not in ["VIX", "BTC-USD", "VFIAX", "VMMXX", "SWVXX", "FXNAX"]]

    for symbol in breadth_symbols:
        data = market_data.get(symbol)
        if data:
            # Get the last available change percentage
            last_record = data[-1] if data else None
            if last_record and 'Change_Pct' in last_record:
                change = last_record['Change_Pct']
                if change > 0.1: # Advancer (up by more than 0.1%)
                    advancers += 1
                elif change < -0.1: # Decliner (down by more than 0.1%)
                    decliners += 1
                else:
                    neutral += 1
    
    breadth_data = {
        "date": datetime.now().strftime('%Y-%m-%d'),
        "advancers": advancers,
        "decliners": decliners,
        "neutral": neutral,
        "total_symbols": len(breadth_symbols)
    }
    save_json(breadth_data, "market_breadth.json")


def main():
    """Main execution function."""
    print("Starting data synchronization...")
    
    # 1. Fetch all market data
    market_data = get_market_data(SYMBOLS)
    save_json(market_data, "market_data_history.json")
    
    # 2. Generate HIBOR rates
    generate_hibor_rates()
    
    # 3. Fetch Fear & Greed Index
    get_fear_greed_index()
    
    # 4. Generate AI Analysis (requires market data)
    generate_ai_analysis(market_data)
    
    # 5. Generate Market Breadth (requires market data)
    generate_market_breadth(market_data)
    
    print("Data synchronization complete.")

if __name__ == "__main__":
    main()
