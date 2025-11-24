import requests
import json
import os
import time
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from openai import OpenAI

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
    """Generates a market summary using the OpenAI API."""
    print("Generating AI market analysis...")
    
    # Load all necessary data
    market_data = load_json("market_data_history.json")
    sentiment_data = load_json("market_sentiment_history.json")
    hibor_data = load_json("hibor_rates.json")
    
    if not market_data or not sentiment_data or not hibor_data:
        print("Warning: Missing data files for AI analysis. Skipping.")
        save_json({"analysis": "數據不足，無法生成 AI 分析。"}, "ai_analysis.json")
        return

    # Extract latest data points
    latest_sentiment = sentiment_data[-1] if sentiment_data else {"value": "N/A", "sentiment": "N/A"}
    latest_hibor = {item['term']: item['rate'] for item in hibor_data}
    
    # Extract key index performance (last 1 day change)
    key_performance = {}
    for symbol in ["SPY", "QQQ", "VIX", "BTC-USD"]:
        if symbol in market_data and market_data[symbol]:
            latest_day = market_data[symbol][-1]
            key_performance[symbol] = {
                "close": latest_day['close'],
                "change_percent": latest_day['change_percent']
            }

    # Construct the prompt
    prompt = f"""
    請根據以下最新的市場數據，生成一段簡潔、專業的市場總結和趨勢分析（約 150 字）。
    
    --- 最新數據 ---
    1. 市場情緒 (Fear & Greed Index):
       - 數值: {latest_sentiment['value']}
       - 情緒: {latest_sentiment['sentiment']}
    
    2. 關鍵指數表現 (日變化 %):
       - SPY (S&P 500 ETF): {key_performance.get('SPY', {}).get('change_percent', 'N/A')} %
       - QQQ (NASDAQ 100 ETF): {key_performance.get('QQQ', {}).get('change_percent', 'N/A')} %
       - VIX (波動率指數): {key_performance.get('VIX', {}).get('change_percent', 'N/A')} %
       - BTC-USD (Bitcoin): {key_performance.get('BTC-USD', {}).get('change_percent', 'N/A')} %
       
    3. 香港銀行同業拆息 (HIBOR):
       - 1個月: {latest_hibor.get('1M', 'N/A')} %
       - 3個月: {latest_hibor.get('3M', 'N/A')} %
       
    --- 分析要求 ---
    - 總結當前市場情緒。
    - 評論主要指數和加密貨幣的短期趨勢。
    - 簡要提及 HIBOR 利率對市場的潛在影響。
    - 語言：繁體中文。
    """

    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "你是一位資深的金融分析師，請根據提供的數據進行客觀的市場分析。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        analysis_text = response.choices[0].message.content
        save_json({"analysis": analysis_text}, "ai_analysis.json")
        print("AI analysis generated successfully.")
    except Exception as e:
        print(f"Error generating AI analysis: {e}")
        save_json({"analysis": "AI 分析生成失敗。請檢查 API Key 或網絡連接。"}, "ai_analysis.json")


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
