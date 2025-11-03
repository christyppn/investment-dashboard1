import os
import json
import requests
from datetime import datetime, timedelta
import time # <-- 確保這行在頂部，沒有縮排

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
        
        records = data.get("result", {}).get("records", [])
        if not records:
            print("No HIBOR data found in API response")
            return []
            
        latest_data = records[0]
        
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
    url = "https://api.alternative.me/fng/"
    try:
        response = requests.get(url, params={"limit": 30}, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        history = []
        data_points = data.get("data", [])
        
        for dp in reversed(data_points):
            ts = datetime.fromtimestamp(int(dp.get("timestamp"))).isoformat() + "Z"
            history.append({
                "date": ts,
                "value": int(dp.get("value")),
                "status": dp.get("value_classification"),
                "region": "US"
            })
        
        print(f"Fetched {len(history)} Fear & Greed Index historical points.")
        latest = history[-1] if history else None
        if latest:
            latest["is_latest"] = True
            print(f"Latest F&G: {latest['value']} ({latest['status']})")
        
        return history
    except Exception as e:
        print(f"Error fetching Fear & Greed Index history: {e}")
        return []

def fetch_alpha_vantage_data(symbol, function, outputsize="compact"):
    # 為了避免 Alpha Vantage 免費 API 的頻率限制 (每分鐘 5 次)，加入 15 秒延遲
    time.sleep(15) # <-- 確保這行有 4 個空格的縮排 (與 print(f"Fetching... 的縮排一致)
    
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

def process_time_series_data(symbol, data, metric_name):
    if not data or "Time Series (Daily)" not in data:
        return []

    time_series = data["Time Series (Daily)"]
    history = []
    
    dates = sorted(time_series.keys(), reverse=True)[:30]
    dates.reverse()

    for i, date_str in enumerate(dates):
        day_data = time_series[date_str]
        latest_close = float(day_data["4. close"])
        volume = int(day_data["5. volume"])

        if i > 0:
            previous_close = float(time_series[dates[i-1]]["4. close"])
            previous_volume = float(time_series[dates[i-1]]["5. volume"])
            change = (latest_close - previous_close) / previous_close * 100
            volume_change = ((volume - previous_volume) / previous_volume * 100) if previous_volume != 0 else 0
        else:
            change = 0.0
            volume_change = 0.0

        history.append({
            "date": date_str + "T00:00:00Z",
            "metric_name": metric_name,
            "change": round(change, 2),
            "volume": volume,
            "volume_change": round(volume_change, 2),
            "close": latest_close
        })

    return history

def fetch_market_data_for_trend():
    print("Fetching market data for trend analysis (Market Breadth and Fund Flows)...")
    
    symbols_to_fetch = {
        "SPY": "S&P 500 Daily Change",
        "QQQ": "NASDAQ 100 Daily Change",
        "DIA": "Dow 30 Daily Change",
     	"XLK": "Technology Sector Volume (XLK)",        # 科技
	    "XLC": "Communication Services Volume (XLC)",   # 通訊服務
	    "XLY": "Consumer Discretionary Volume (XLY)",   # 非必需消費品
	    "XLP": "Consumer Staples Volume (XLP)",         # 必需消費品
	    "XLV": "Health Care Volume (XLV)",              # 醫療保健
	    "XLF": "Financial Sector Volume (XLF)",         # 金融
	    "XLE": "Energy Sector Volume (XLE)",            # 能源
	    "XLI": "Industrial Sector Volume (XLI)",        # 工業
	    "XLB": "Materials Sector Volume (XLB)",         # 原材料
	    "XLU": "Utilities Sector Volume (XLU)",         # 公用事業
	    "GLD": "Gold Fund Volume (GLD)",                # 黃金/貴金屬
	    "ROBO": "Robotics & AI Volume (ROBO)",          # 機器人/AI
	    "SMH": "Semiconductor Volume (SMH)",            # 半導體
	    "IWM": "Small Cap Volume (IWM)"                 # 小型股
    }

    all_market_data = []

    for symbol, metric_name in symbols_to_fetch.items():
        data = fetch_alpha_vantage_data(symbol, "TIME_SERIES_DAILY", outputsize="full")
        
        if data:
            processed_data = process_time_series_data(symbol, data, metric_name)
            all_market_data.extend(processed_data)
        
    print(f"Fetched {len(all_market_data)} total market data points.")
    return all_market_data

def fetch_money_fund_data():
    print("Fetching Money Fund data...")
    fund_symbols = {
        "VFIAX": "Vanguard 500 Index Fund",
        "VTSAX": "Vanguard Total Stock Market Index Fund",
        # Add more fund symbols as needed
    }
    fund_data = []

    for symbol, name in fund_symbols.items():
        ts_data = fetch_alpha_vantage_data(symbol, "TIME_SERIES_DAILY", outputsize="compact")
        
        if ts_data and "Time Series (Daily)" in ts_data:
            time_series = ts_data["Time Series (Daily)"]
            latest_date = sorted(time_series.keys(), reverse=True)[0]
            latest_day_data = time_series[latest_date]
            
            previous_date = sorted(time_series.keys(), reverse=True)[1] if len(time_series) > 1 else None
            previous_close = float(time_series[previous_date]["4. close"]) if previous_date else float(latest_day_data.get("4. close", 0))

            try:
                latest_close = float(latest_day_data.get("4. close", 0))
                change = latest_close - previous_close
                change_percent = (change / previous_close * 100) if previous_close != 0 else 0
                
                latest_data = {
                    "fund_name": name,
                    "symbol": symbol,
                    "price": latest_close,
                    "change": round(change, 2),
                    "change_percent": f"{round(change_percent, 2)}%",
                    "latest_trading_day": latest_date,
                    "timestamp": datetime.now().isoformat() + "Z"
                }
                fund_data.append(latest_data)
                print(f"Fetched time series data for {name}")
            except Exception as e:
                print(f"Error processing time series for {name}: {e}")
        else:
            print(f"No TIME_SERIES_DAILY data found for {name}.")
    
    return fund_data

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
    
    # 1. Fetch and write HIBOR rates (Latest data only)
    hibor_data = fetch_hibor_rates()
    if hibor_data:
        write_to_file(hibor_data, "hibor_rates.json")
    
    # 2. Fetch and write Fear & Greed Index (Historical data for trend)
    fng_history = fetch_fear_greed_index_history()
    if fng_history:
        write_to_file(fng_history, "market_sentiment_history.json")
    
    # 3. Fetch and write Market Breadth/Fund Flows (Historical data for trend)
    market_data_history = fetch_market_data_for_trend()
    if market_data_history:
        write_to_file(market_data_history, "market_data_history.json")

    # 4. Fetch and write Money Fund data (Latest data only)
    money_fund_data = fetch_money_fund_data()
    if money_fund_data:
        write_to_file(money_fund_data, "money_fund_data.json")

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
