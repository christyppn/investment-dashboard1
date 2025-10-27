import os
import json
import requests
from datetime import datetime, timedelta

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
        response = requests.get(url, timeout=30 )
        response.raise_for_status()
        data = response.json()
        
        # 提取最新數據
        records = data.get("result", {}).get("records", [])
        if not records:
            print("No HIBOR data found in API response")
            return []
            
        latest_data = records[0]
        
        # 轉換為所需格式 (已修正為 ir_1m, ir_3m, ir_6m)
        hibor_data = [
            {"id": "1", "term": "1M", "rate": float(latest_data.get("ir_1m", 0)), "timestamp": datetime.now().isoformat() + "Z"},
            {"id": "2", "term": "3M", "rate": float(latest_data.get("ir_3m", 0)), "timestamp": datetime.now().isoformat() + "Z"},
            {"id": "3", "term": "6M", "rate": float(latest_data.get("ir_6m", 0)), "timestamp": datetime.now().isoformat() + "Z"},
        ]
        print(f"Fetched HIBOR rates: {hibor_data}")
        return hibor_data
    except Exception as e:
        print(f"Error fetching HIBOR rates: {e}")
        return []

def fetch_fear_greed_index_history():
    print("Fetching Fear & Greed Index History...")
    # Alternative.me API supports historical data up to 30 days
    url = "https://api.alternative.me/fng/"
    try:
        # Fetch last 30 data points for trend
        response = requests.get(url, params={"limit": 30}, timeout=30 )
        response.raise_for_status()
        data = response.json()
        
        history = []
        data_points = data.get("data", [])
        
        # Reformat data for frontend charting (oldest first)
        for dp in reversed(data_points):
            # Convert timestamp from seconds (string) to ISO format
            ts = datetime.fromtimestamp(int(dp.get("timestamp"))).isoformat() + "Z"
            history.append({
                "date": ts,
                "value": int(dp.get("value")),
                "status": dp.get("value_classification"),
                "region": "US"
            })
        
        print(f"Fetched {len(history)} Fear & Greed Index historical points.")
        # Also include the latest status for the main card
        latest = history[-1] if history else None
        if latest:
            latest["is_latest"] = True
            print(f"Latest F&G: {latest['value']} ({latest['status']})")
        
        return history
    except Exception as e:
        print(f"Error fetching Fear & Greed Index history: {e}")
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
        response = requests.get(base_url, params=params, timeout=30 )
        response.raise_for_status()
        data = response.json()
        if "Error Message" in data:
            print(f"Alpha Vantage Error: {data['Error Message']}")
            return None
        if "Note" in data:
            print(f"Alpha Vantage Note: {data['Note']}")
            # This is often a rate limit note, we treat it as a temporary failure
            return None
        return data
    except Exception as e:
        print(f"Error fetching Alpha Vantage data for {symbol}: {e}")
        return None

def process_time_series_data(symbol, data, metric_name):
    """Processes Alpha Vantage Time Series data for trend analysis."""
    if not data or "Time Series (Daily)" not in data:
        return []

    time_series = data["Time Series (Daily)"]
    history = []
    
    # Get last 30 days of data for trend
    dates = sorted(time_series.keys(), reverse=True)[:30]
    dates.reverse() # Oldest first for charting

    for i, date_str in enumerate(dates):
        day_data = time_series[date_str]
        
        # Calculate daily change for market breadth
        if i > 0:
            previous_close = float(time_series[dates[i-1]]["4. close"])
            latest_close = float(day_data["4. close"])
            change = (latest_close - previous_close) / previous_close * 100
        else:
            change = 0.0 # No change for the first day

        # Use volume for fund flow
        volume = int(day_data["5. volume"])

        history.append({
            "date": date_str + "T00:00:00Z", # Add time component for consistency
            "metric_name": metric_name,
            "change": round(change, 2),
            "volume": volume,
            "close": float(day_data["4. close"])
        })
    
    return history

def fetch_market_data_for_trend():
    print("Fetching market data for trend analysis (Market Breadth and Fund Flows)...")
    
    # Symbols for Market Breadth (Daily Change) and Fund Flow (Volume)
    # Using major ETFs as proxies for indices and sectors
    symbols_to_fetch = {
        # Market Breadth (Daily Change)
        "SPY": "S&P 500 Daily Change",      # US (S&P 500)
        "QQQ": "NASDAQ 100 Daily Change",   # US (NASDAQ 100)
        "DIA": "Dow 30 Daily Change",       # US (Dow Jones)
        # Note: Alpha Vantage does not have HK index data (HSI) easily accessible via free API.
        # We will use the US proxies for now and note the limitation.

        # Fund Flows (Volume)
        "XLF": "Financial Sector Volume",
        "XLK": "Technology Sector Volume",
        "XLE": "Energy Sector Volume",
        "XLP": "Consumer Staples Volume",
        "XLY": "Consumer Discretionary Volume",
        "IWM": "Small Cap (Russell 2000) Volume"
    }

    all_market_data = []

    for symbol, metric_name in symbols_to_fetch.items():
        # Use TIME_SERIES_DAILY for both change (breadth) and volume (flow)
        data = fetch_alpha_vantage_data(symbol, "TIME_SERIES_DAILY", outputsize="full")
        
        if data:
            processed_data = process_time_series_data(symbol, data, metric_name)
            all_market_data.extend(processed_data)
        
    print(f"Fetched {len(all_market_data)} total market data points.")
    return all_market_data

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
    # We assume the user has set the API key by now
    print(f"Alpha Vantage API Key: {'Set' if ALPHA_VANTAGE_API_KEY != 'YOUR_ALPHA_VANTAGE_API_KEY' else 'Not Set'}")
    
    # 1. Fetch and write HIBOR rates (Latest data only)
    hibor_data = fetch_hibor_rates()
    if hibor_data:
        write_to_file(hibor_data, "hibor_rates.json")
    
    # 2. Fetch and write Fear & Greed Index (Historical data for trend)
    fng_history = fetch_fear_greed_index_history()
    if fng_history:
        # The frontend will use this file for both latest status and trend chart
        write_to_file(fng_history, "market_sentiment_history.json")
    
    # 3. Fetch and write Market Breadth/Fund Flows (Historical data for trend)
    market_data_history = fetch_market_data_for_trend()
    if market_data_history:
        # This single file will contain all historical data for market breadth (change) and fund flows (volume)
        write_to_file(market_data_history, "market_data_history.json")

   # 4. Fetch and write Money Fund data (Latest data only)
    money_fund_data = fetch_money_fund_data()
    if money_fund_data:
        write_to_file(money_fund_data, "money_fund_data.json")

    # The original market_breadth.json and fund_flows.json are now obsolete or need to be simplified
    # For simplicity and to avoid breaking the existing frontend structure, let's keep the old files for latest data
    # and use the new files for historical/expanded data.
    
    # Extract latest data for the original files (to keep the current dashboard cards working)
    if market_data_history:
        latest_spy = next((d for d in reversed(market_data_history) if d["metric_name"] == "S&P 500 Daily Change"), None)
        if latest_spy:
            market_breadth_data = [{
                "id": "1",
                "metric_name": "SPY Daily Change",
                "region": "US",
                "value": latest_spy["change"],
                "timestamp": latest_spy["date"]
            }]
            write_to_file(market_breadth_data, "market_breadth.json")
            
        latest_qqq_volume = next((d for d in reversed(market_data_history) if d["metric_name"] == "Technology Sector Volume"), None)
        if latest_qqq_volume:
            fund_flows_data = [{
                "id": "1",
                "region": "US",
                "sector": "Technology (XLK Volume)",
                "flow_type": "Volume",
                "amount": latest_qqq_volume["volume"],
                "timestamp": latest_qqq_volume["date"]
            }]
            write_to_file(fund_flows_data, "fund_flows.json")

    print("Data synchronization process finished.")

if __name__ == "__main__":
    main()


