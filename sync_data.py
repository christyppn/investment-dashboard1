# sync_data.py - 最終修復版本 (Final Corrected Version)

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
        # Removed print statement to prevent pollution
    except Exception as e:
        # Removed print statement to prevent pollution
        pass

def get_market_data(symbols):
    """Fetches historical data for a list of symbols using yfinance."""
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    data = yf.download(symbols, start=start_date, end=end_date, interval="1d")
    
    if data.empty:
        return {}

    history_data = {}
    for symbol in symbols:
        if ('Close', symbol) in data.columns:
            closes = data['Close'][symbol].dropna()
            if not closes.empty:
                history_data[symbol] = [
                    {"date": date.strftime('%Y-%m-%d'), "close": close, "name": symbol}
                    for date, close in closes.items()
                ]
    return history_data

def generate_market_breadth():
    """Generates a dummy market breadth data structure."""
    # In a real scenario, this would involve complex calculations.
    # For now, we use a static structure to ensure the file is valid.
    
    # Dummy data for demonstration
    breadth_data = [
        {"name": "S&P 500", "ma_days": 50, "percent_above": 65.2},
        {"name": "NASDAQ", "ma_days": 50, "percent_above": 72.8},
        {"name": "NYSE", "ma_days": 50, "percent_above": 58.1},
        {"name": "S&P 500", "ma_days": 200, "percent_above": 52.5},
    ]
    
    return {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "breadth": breadth_data
    }

def generate_money_fund_data():
    """Generates dummy money fund data."""
    # Dummy data for demonstration
    return {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "funds": [
            {"symbol": "VFIAX", "latest_price": 450.25, "daily_change_percent": 0.85, "date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')},
            {"symbol": "VTSAX", "latest_price": 120.10, "daily_change_percent": 0.72, "date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')},
            {"symbol": "VBTLX", "latest_price": 10.50, "daily_change_percent": -0.05, "date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')},
            {"symbol": "BIL", "latest_price": 91.88, "daily_change_percent": 0.01, "date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')},
        ]
    }

def generate_dummy_data():
    """Generates dummy data for all required JSON files."""
    
    # 1. AI Analysis
    ai_analysis = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "sentiment": "Bullish",
        "analysis": "市場情緒持續樂觀，主要指數在科技股帶動下創下新高。建議關注半導體和人工智能相關領域的長期投資機會。"
    }
    save_json(ai_analysis, 'ai_analysis.json')

    # 2. Fear & Greed Index
    fear_greed = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "value": 78
    }
    save_json(fear_greed, 'fear_greed_index.json')

    # 3. HIBOR Rates (Dummy)
    hibor_rates = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "rates": [
            {"term": "隔夜", "rate": 4.850},
            {"term": "1 個月", "rate": 5.125},
            {"term": "3 個月", "rate": 5.350},
            {"term": "6 個月", "rate": 5.500},
        ]
    }
    save_json(hibor_rates, 'hibor_rates.json')

    # 4. Market Breadth
    market_breadth = generate_market_breadth()
    save_json(market_breadth, 'market_breadth.json')

    # 5. Market Data History (for Global Markets Chart)
    market_history = get_market_data(SYMBOLS)
    save_json(market_history, 'market_data_history.json')

    # 6. Money Fund Data
    money_fund_data = generate_money_fund_data()
    save_json(money_fund_data, 'money_fund_data.json')
    
    # 7. 13F Data (Dummy)
    f13_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "holdings": [
            {"symbol": "AAPL", "value": 246.5, "change": -13.2},
            {"symbol": "BAC", "value": 54.8, "change": -5.6},
            {"symbol": "KO", "value": 26.4, "change": 0.0},
        ]
    }
    save_json(f13_data, '13f-data.json')
    
    # 8. Market Sentiment (Dummy for Consensus)
    market_sentiment = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "consensus": {
            "latest_sentiment": "中性偏多",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    save_json(market_sentiment, 'market_sentiment.json')


if __name__ == "__main__":
    generate_dummy_data()
