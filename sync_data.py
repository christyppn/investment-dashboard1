import os
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# --- Configuration --- #
DATA_DIR = "data"  # 數據將儲存在此目錄
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "YOUR_ALPHA_VANTAGE_API_KEY")

# 確保數據目錄存在
os.makedirs(DATA_DIR, exist_ok=True)

# --- Data Fetching Functions --- #

def fetch_hibor_rates():
    print("Fetching HIBOR rates...")
    url = "https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # 提取最新數據
        records = data.get("result", {}).get("records", [])
        if not records:
            print("No HIBOR data found in API response")
            return []
            
        latest_data = records[0]
        
        # 轉換為所需格式
        hibor_data = [
            {"id": "1", "term": "1M", "rate": float(latest_data.get("HIBOR_1M", 0)), "timestamp": datetime.now().isoformat() + "Z"},
            {"id": "2", "term": "3M", "rate": float(latest_data.get("HIBOR_3M", 0)), "timestamp": datetime.now().isoformat() + "Z"},
            {"id": "3", "term": "6M", "rate": float(latest_data.get("HIBOR_6M", 0)), "timestamp": datetime.now().isoformat() + "Z"},
        ]
        print(f"Fetched HIBOR rates: {hibor_data}")
        return hibor_data
    except Exception as e:
        print(f"Error fetching HIBOR rates: {e}")
        return []

def fetch_fear_greed_index():
    print("Fetching Fear & Greed Index...")
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # 提取當前指數值
        score = data.get("fear_and_greed", {}).get("score")
        rating = data.get("fear_and_greed", {}).get("rating")
        
        if score is not None:
            fng_data = [
                {
                    "id": "1",
                    "indicator_name": "Fear & Greed Index",
                    "region": "US",
                    "value": int(score),
                    "status": rating or "Unknown",
                    "timestamp": datetime.now().isoformat() + "Z"
                }
            ]
            print(f"Fetched Fear & Greed Index: {fng_data}")
            return fng_data
        else:
            print("Could not find Fear & Greed Index value.")
            return []
    except Exception as e:
        print(f"Error fetching Fear & Greed Index: {e}")
        return []

def fetch_alpha_vantage_data(symbol, function, outputsize="compact"):
    print(f"Fetching Alpha Vantage data for {symbol} ({function})...")
    base_url = "https://www.alphavantage.co/query"
    params = {
        "function": function,
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
        "outputsize": outputsize
    }
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "Error Message" in data:
            print(f"Alpha Vantage Error: {data['Error Message']}")
            return None
        if "Note" in data:
            print(f"Alpha Vantage Note: {data['Note']}")
            return None
        return data
    except Exception as e:
        print(f"Error fetching Alpha Vantage data for {symbol}: {e}")
        return None

def fetch_market_breadth():
    print("Fetching market breadth data...")
    spy_data = fetch_alpha_vantage_data("SPY", "TIME_SERIES_DAILY")
    if spy_data and "Time Series (Daily)" in spy_data:
        time_series = spy_data["Time Series (Daily)"]
        dates = list(time_series.keys())
        if len(dates) >= 2:
            latest_close = float(time_series[dates[0]]["4. close"])
            previous_close = float(time_series[dates[1]]["4. close"])
            change = (latest_close - previous_close) / previous_close * 100
            
            market_breadth_data = [
                {
                    "id": "1",
                    "metric_name": "SPY Daily Change",
                    "region": "US",
                    "value": round(change, 2),
                    "timestamp": datetime.now().isoformat() + "Z"
                }
            ]
            print(f"Fetched Market Breadth: {market_breadth_data}")
            return market_breadth_data
    print("Could not fetch market breadth data.")
    return []

def fetch_fund_flows():
    print("Fetching fund flows data...")
    qqq_data = fetch_alpha_vantage_data("QQQ", "TIME_SERIES_DAILY")
    if qqq_data and "Time Series (Daily)" in qqq_data:
        time_series = qqq_data["Time Series (Daily)"]
        dates = list(time_series.keys())
        if len(dates) >= 1:
            latest_volume = int(time_series[dates[0]]["5. volume"])
            
            fund_flows_data = [
                {
                    "id": "1",
                    "region": "US",
                    "sector": "Technology (QQQ Volume)",
                    "flow_type": "Volume",
                    "amount": latest_volume,
                    "timestamp": datetime.now().isoformat() + "Z"
                }
            ]
            print(f"Fetched Fund Flows: {fund_flows_data}")
            return fund_flows_data
    print("Could not fetch fund flows data.")
    return []

# --- File Writing Function --- #

def write_to_file(data, filename):
    try:
        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Successfully wrote {filename}")
        return True
    except Exception as e:
        print(f"Error writing {filename}: {e}")
        return False

# --- Main Sync Logic --- #

def main():
    print("Starting data synchronization process...")
    print(f"Alpha Vantage API Key: {'Set' if ALPHA_VANTAGE_API_KEY != 'YOUR_ALPHA_VANTAGE_API_KEY' else 'Not Set'}")
    
    # Fetch and write HIBOR rates
    hibor_data = fetch_hibor_rates()
    if hibor_data:
        write_to_file(hibor_data, "hibor_rates.json")
    
    # Fetch and write Fear & Greed Index
    fng_data = fetch_fear_greed_index()
    if fng_data:
        write_to_file(fng_data, "market_sentiment.json")
    
    # Fetch and write Market Breadth
    market_breadth_data = fetch_market_breadth()
    if market_breadth_data:
        write_to_file(market_breadth_data, "market_breadth.json")
    
    # Fetch and write Fund Flows
    fund_flows_data = fetch_fund_flows()
    if fund_flows_data:
        write_to_file(fund_flows_data, "fund_flows.json")
    
    print("Data synchronization process finished.")

if __name__ == "__main__":
    main()

