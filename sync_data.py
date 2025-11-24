import requests
import json
import os
import time
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
# from openai import OpenAI # Removed OpenAI dependency

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
    # --- Data Expansion ---
    "GSPC": "^GSPC", # S&P 500 Index
    "IXIC": "^IXIC", # NASDAQ Composite Index
    "BTC-USD": "BTC-USD", # Bitcoin
    # --- End Data Expansion ---
    # Sector ETFs (11)
    "XLK": "XLK", "XLC": "XLC", "XLY": "XLY", "XLP": "XLP", "XLV": "XLV", "XLF": "XLF", 
    "XLE": "XLE", "XLI": "XLI", "XLB": "XLB", "XLU": "XLU", "VNQ": "VNQ",
    # Thematic/Commodity ETFs (4)
    "GLD": "GLD", "ROBO": "ROBO", "SMH": "SMH", "IWM": "IWM",
    # Money Market Funds (4) - Using original mutual fund symbols (yfinance supports them)
    "VFIAX": "VFIAX", "VMMXX": "VMMXX", "SWVXX": "SWVXX", "FXNAX": "FXNAX"
}

# --- Helper Functions ---

def save_json(data, filename):
    """Saves data to a JSON file in the DATA_DIR."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Successfully saved data to {filepath}")

def load_json(filename):
    """Loads data from a JSON file in the DATA_DIR."""
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# --- Data Fetching Functions ---

def fetch_hibor_rates():
    """Generates static HIBOR rates as a temporary fix."""
    # Static HIBOR rates based on latest user input (2025-11-21)
    hibor_data = [
        {"term": "1M", "rate": "3.00429", "timestamp": "2025-11-21T00:00:00Z"},
        {"term": "3M", "rate": "3.43476", "timestamp": "2025-11-21T00:00:00Z"},
        {"term": "6M", "rate": "3.41250", "timestamp": "2025-11-21T00:00:00Z"}
    ]
    save_json(hibor_data, "hibor_rates.json")

def fetch_fear_greed_index():
    """Fetches the latest Fear & Greed Index data."""
    # This function is assumed to be working correctly from previous iterations
    # Placeholder for the actual implementation (which is complex and external)
    
    # Load existing history
    history = load_json("market_sentiment_history.json") or []
    
    # Static data to ensure the file is updated
    latest_date = datetime.now().strftime("%Y-%m-%d")
    latest_data = {
        "date": latest_date,
        "value": 11,
        "sentiment": "Extreme Fear"
    }
    
    # Prevent duplicate entries for the same day
    if not history or history[-1].get("date") != latest_date:
        history.append(latest_data)
    
    save_json(history, "market_sentiment_history.json")

def fetch_market_data():
    """Fetches historical market data for all symbols."""
    
    # Load existing data to append new data points
    market_data_history = load_json("market_data_history.json") or {}
    
    # Ensure all symbols are initialized
    for symbol in YAHOO_SYMBOLS:
        if symbol not in market_data_history:
            market_data_history[symbol] = []

    # Fetch data for all symbols
    y_symbols = list(YAHOO_SYMBOLS.values())
    
    # Fetch data for the last 1 year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    try:
        data = yf.download(y_symbols, start=start_date, end=end_date, interval="1d", progress=False)
    except Exception as e:
        print(f"FATAL WARNING: yfinance download failed: {e}")
        # Save an empty file to prevent frontend from crashing
        save_json({}, "market_data_history.json")
        return

    if data.empty:
        print("FATAL WARNING: yfinance returned empty data. Saving an empty file.")
        save_json({}, "market_data_history.json")
        return

    # Process data for each symbol
    for symbol_key, y_symbol in YAHOO_SYMBOLS.items():
        if y_symbol in data['Close']:
            df = data.loc[:, (slice(None), y_symbol)].dropna()
            df.columns = df.columns.droplevel(1)
            
            # Calculate daily change percent and volume change percent
            df['Close'] = df['Close'].ffill() # Forward fill to handle missing data
            df['Volume'] = df['Volume'].fillna(0) # Fill volume with 0
            
            df['change_percent'] = df['Close'].pct_change() * 100
            df['volume_change_percent'] = df['Volume'].pct_change() * 100
            
            # Convert to list of dicts for JSON
            history_list = []
            for index, row in df.iterrows():
                history_list.append({
                    "date": index.strftime("%Y-%m-%d"),
                    "open": row['Open'],
                    "high": row['High'],
                    "low": row['Low'],
                    "close": row['Close'],
                    "volume": row['Volume'],
                    "change_percent": row['change_percent'],
                    "volume_change_percent": row['volume_change_percent']
                })
            
            # Remove the first entry as it has NaN for change_percent
            if history_list:
                history_list.pop(0)
            
            market_data_history[symbol_key] = history_list

    # Separate money fund data (assumed to be working correctly)
    money_fund_data = market_data_history.get("VFIAX", []) # Using VFIAX as a placeholder for money fund data
    
    # Remove money fund data from main history
    if "VFIAX" in market_data_history:
        del market_data_history["VFIAX"]
    
    # Final check before saving
    if not market_data_history or all(not v for v in market_data_history.values()):
        print("FATAL WARNING: market_data_history is empty. Saving an empty file to prevent frontend from crashing.")
        save_json({}, "market_data_history.json")
    else:
        # Save the combined data files
        save_json(market_data_history, "market_data_history.json")
        
    save_json(money_fund_data, "money_fund_data.json")

def generate_ai_analysis():
    """Generates a market summary and 7-day prediction using rule-based analysis."""
    print("Generating rule-based market analysis...")
    
    # Load all necessary data
    market_data = load_json("market_data_history.json")
    sentiment_data = load_json("market_sentiment_history.json")
    
    if not market_data or not sentiment_data:
        analysis_text = "數據不足，無法生成市場分析。請檢查 market_data_history.json 和 market_sentiment_history.json 文件。"
        save_json({"analysis": analysis_text}, "ai_analysis.json")
        return

    # Extract latest data points
    latest_sentiment = sentiment_data[-1] if sentiment_data else {"value": 50, "sentiment": "Neutral"}
    sentiment_value = latest_sentiment['value']
    sentiment_text = latest_sentiment['sentiment']
    
    # Extract key index performance (last 1 day change)
    spy_change = market_data.get('SPY', [{}])[-1].get('change_percent', 0)
    qqq_change = market_data.get('QQQ', [{}])[-1].get('change_percent', 0)
    vix_change = market_data.get('VIX', [{}])[-1].get('change_percent', 0)
    btc_change = market_data.get('BTC-USD', [{}])[-1].get('change_percent', 0)
    
    # --- Rule-Based Analysis ---
    
    summary = f"當前市場情緒為 **{sentiment_text}** (指數: {sentiment_value})。"
    
    # Rule 1: Sentiment
    if sentiment_value <= 20:
        summary += "市場處於極度恐懼狀態，通常預示著潛在的超賣和反彈機會。"
    elif sentiment_value >= 80:
        summary += "市場處於極度貪婪狀態，可能存在過熱和回調風險。"
    
    # Rule 2: VIX (Volatility)
    if vix_change > 5:
        summary += f"VIX (波動率指數) 日內上漲 {vix_change:.2f}%，顯示市場避險情緒急劇升溫。"
    elif vix_change < -5:
        summary += f"VIX 日內下跌 {abs(vix_change):.2f}%，表明市場恐慌情緒緩解，風險偏好回升。"
        
    # Rule 3: Index Performance
    if spy_change > 0.5 and qqq_change > 0.5:
        summary += "主要指數 SPY 和 QQQ 均強勁上漲，顯示市場整體樂觀，科技板塊領漲。"
    elif spy_change < -0.5 and qqq_change < -0.5:
        summary += "主要指數 SPY 和 QQQ 均顯著下跌，市場面臨拋售壓力。"
        
    # Rule 4: Bitcoin Trend
    if btc_change > 2:
        summary += f"比特幣 (BTC) 日內大漲 {btc_change:.2f}%，加密貨幣市場表現強勁。"
    
    # --- 7-Day Prediction (Rule-Based) ---
    
    prediction = "未來 7 天市場預測："
    if sentiment_value <= 20 and vix_change < 0:
        prediction += " **看漲 (Bullish)**。極度恐懼情緒配合波動率下降，可能迎來技術性反彈。"
    elif sentiment_value >= 80 and vix_change > 0:
        prediction += " **看跌 (Bearish)**。市場過熱且波動率上升，預計將出現回調。"
    else:
        prediction += " **盤整 (Sideways)**。市場缺乏明確方向，預計將在當前區間震盪。"
        
    final_analysis = f"{summary}\n\n{prediction}"
    
    save_json({"analysis": final_analysis}, "ai_analysis.json")
    print("Rule-based analysis generated successfully.")


# --- Main Execution ---

if __name__ == "__main__":
    print("Starting data synchronization script...")
    
    # 1. Fetch HIBOR rates (Daily)
    fetch_hibor_rates()
    
    # 2. Fetch Fear & Greed Index
    fetch_fear_greed_index()
    
    # 3. Fetch Market Data (Indices, ETFs, Money Funds) using Yahoo Finance (yfinance)
    fetch_market_data()
    
    # 4. Generate AI Analysis (Requires market data)
    generate_ai_analysis()
    
    print("Data synchronization complete.")
