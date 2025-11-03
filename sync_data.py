import os
import json
import requests
from datetime import datetime, timedelta
import time

# --- Configuration --- #
DATA_DIR = "data"  # 數據將儲存在此目錄
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "YOUR_ALPHA_VANTAGE_API_KEY")

# 確保數據目錄存在
os.makedirs(DATA_DIR, exist_ok=True)

# --- Utility Functions --- #

def write_to_file(data, filename):
    """將數據寫入 JSON 文件"""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Successfully wrote {filename}")
        return True
    except Exception as e:
        print(f"Error writing {filename}: {e}")
        return False

def fetch_alpha_vantage_data(symbol, function, outputsize="compact"):
    """從 Alpha Vantage 獲取數據，並加入延遲以避免頻率限制"""
    # 為了避免 Alpha Vantage 免費 API 的頻率限制 (每分鐘 5 次)，加入 15 秒延遲
    time.sleep(15)
    
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
            print(f"Alpha Vantage Error for {symbol}: {data['Error Message']}")
            return None
        if "Note" in data:
            print(f"Alpha Vantage Note for {symbol}: {data['Note']}")
            return None
            
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Alpha Vantage data for {symbol}: {e}")
        return None

# --- Data Fetching Functions --- #

def fetch_hibor_rates():
    """獲取香港 HIBOR 利率"""
    print("Fetching HIBOR rates...")
    url = "https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily"
    try:
        response = requests.get(url, timeout=30 )
        response.raise_for_status()
        data = response.json()
        
        records = data.get("result", {}).get("records", [])
        if not records:
            print("No HIBOR data found in API response")
            return []
            
        latest_data = records[0]
        
        # 修正後的鍵名：ir_1m, ir_3m, ir_6m
        hibor_data = [
            {"id": "1", "term": "1M", "rate": float(latest_data.get("ir_1m", 0)), "timestamp": datetime.now().isoformat() + "Z"},
            {"id": "2", "term": "3M", "rate": float(latest_data.get("ir_3m", 0)), "timestamp": datetime.now().isoformat() + "Z"},
            {"id": "3", "term": "6M", "rate": float(latest_data.get("ir_6m", 0)), "timestamp": datetime.now().isoformat() + "Z"},
        ]
        return hibor_data
    except Exception as e:
        print(f"Error fetching HIBOR rates: {e}")
        return []

def fetch_fear_greed_index():
    """獲取恐懼與貪婪指數歷史數據"""
    print("Fetching Fear & Greed Index History...")
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    try:
        response = requests.get(url, timeout=30 )
        response.raise_for_status()
        data = response.json()
        
        fng_data = []
        # 獲取歷史數據，只取最近 30 天
        history = data.get("fear_and_greed_historical", [])
        for item in history[-30:]:
            fng_data.append({
                "date": datetime.fromtimestamp(item["timestamp"] / 1000).isoformat() + "Z",
                "value": item["score"],
                "rating": item["rating"]
            })
            
        print(f"Fetched {len(fng_data)} Fear & Greed Index historical points.")
        return fng_data
    except Exception as e:
        print(f"Error fetching Fear & Greed Index: {e}")
        return []

def process_time_series_data(data, symbol, name):
    """處理 Alpha Vantage 的 TIME_SERIES_DAILY 數據，計算日變動和成交量變動"""
    time_series = data.get("Time Series (Daily)", {})
    if not time_series:
        return []

    # 獲取最新的 30 天數據
    dates = sorted(time_series.keys(), reverse=True)[:30]
    processed_data = []

    for i, date in enumerate(dates):
        latest_day_data = time_series[date]
        
        # 獲取前一天的數據
        previous_date = dates[i+1] if i + 1 < len(dates) else None
        
        # --- Price Change Calculation ---
        previous_close = float(time_series[previous_date]["4. close"]) if previous_date else float(latest_day_data.get("4. close", 0))
        latest_close = float(latest_day_data.get("4. close", 0))
        
        # 避免除以零錯誤
        if previous_close == 0:
            change_percent = 0
        else:
            change_percent = (latest_close - previous_close) / previous_close * 100
        
        # --- Volume Change Calculation ---
        previous_volume = float(time_series[previous_date]["5. volume"]) if previous_date else 0
        latest_volume = float(latest_day_data.get("5. volume", 0))
        
        # 避免除以零錯誤
        if previous_volume == 0:
            volume_change = 0
        else:
            volume_change = (latest_volume - previous_volume) / previous_volume * 100
        
        processed_data.append({
            "date": datetime.strptime(date, "%Y-%m-%d").isoformat() + "Z",
            "symbol": symbol,
            "metric_name": name,
            "close": latest_close,
            "change": round(change_percent, 2),
            "volume": int(latest_day_data.get("5. volume", 0)),
            "volume_change": round(volume_change, 2)
        })

    return processed_data

def fetch_market_data_for_trend():
    """獲取所有市場廣度和資金流向的歷史數據"""
    print("Fetching market data for trend analysis (Market Breadth and Fund Flows)...")
    
    # 擴展後的 ETF 列表，用於市場廣度和資金流向
    symbols_to_fetch = {
        # Market Breadth (Daily Change)
        "SPY": "S&P 500 Daily Change",
        "QQQ": "NASDAQ 100 Daily Change",
        "DIA": "Dow 30 Daily Change",
        
        # Fund Flows (Volume) - 擴展後的行業板塊
        "XLK": "Technology Sector Volume (XLK)",
        "XLC": "Communication Services Volume (XLC)",
        "XLY": "Consumer Discretionary Volume (XLY)",
        "XLP": "Consumer Staples Volume (XLP)",
        "XLV": "Health Care Volume (XLV)",
        "XLF": "Financial Sector Volume (XLF)",
        "XLE": "Energy Sector Volume (XLE)",
        "XLI": "Industrial Sector Volume (XLI)",
        "XLB": "Materials Sector Volume (XLB)",
        "XLU": "Utilities Sector Volume (XLU)",
        "GLD": "Gold Fund Volume (GLD)",
        "ROBO": "Robotics & AI Volume (ROBO)",
        "SMH": "Semiconductor Volume (SMH)",
        "IWM": "Small Cap Volume (IWM)"
    }
    
    all_market_data = []
    for symbol, name in symbols_to_fetch.items():
        data = fetch_alpha_vantage_data(symbol, "TIME_SERIES_DAILY", "compact")
        if data:
            all_market_data.extend(process_time_series_data(data, symbol, name))
            
    print(f"Fetched {len(all_market_data)} total market data points.")
    return all_market_data

def fetch_money_fund_data():
    """獲取貨幣基金數據 (使用 TIME_SERIES_DAILY 替代 FUND_HOLDINGS)"""
    print("Fetching Money Fund data...")
    
    # 使用 TIME_SERIES_DAILY 獲取基金價格數據
    funds_to_fetch = {
        "VFIAX": "Vanguard 500 Index Fund",
        "VTSAX": "Vanguard Total Stock Market Index Fund",
        "VBTLX": "Vanguard Total Bond Market Index Fund", # 債券
        "VMMXX": "Vanguard Money Market Fund" # 貨幣
    }
    
    fund_data = []
    for symbol, name in funds_to_fetch.items():
        data = fetch_alpha_vantage_data(symbol, "TIME_SERIES_DAILY", "compact")
        if data:
            time_series = data.get("Time Series (Daily)", {})
            if not time_series:
                continue
                
            dates = sorted(time_series.keys(), reverse=True)
            latest_date = dates[0]
            latest_day_data = time_series[latest_date]
            
            # 獲取前一天的數據
            previous_date = dates[1] if len(dates) > 1 else None
            previous_close = float(time_series[previous_date]["4. close"]) if previous_date else float(latest_day_data.get("4. close", 0))

            try:
                latest_close = float(latest_day_data.get("4. close", 0))
                
                # 避免除以零錯誤
                if previous_close == 0:
                    change = 0
                    change_percent = 0
                else:
                    change = latest_close - previous_close
                    change_percent = (change / previous_close) * 100
                
                latest_data = {
                    "fund_name": name,
                    "symbol": symbol,
                    "price": round(latest_close, 2),
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

# --- Main Sync Logic --- #

def main():
    print("Starting data synchronization process...")
    print(f"Alpha Vantage API Key: {'Set' if ALPHA_VANTAGE_API_KEY != 'YOUR_ALPHA_VANTAGE_API_KEY' else 'Not Set'}")
    
    # 1. Fetch and write HIBOR rates
    hibor_data = fetch_hibor_rates()
    if hibor_data:
        write_to_file(hibor_data, "hibor_rates.json")
    
    # 2. Fetch and write Fear & Greed Index History
    fng_data = fetch_fear_greed_index()
    if fng_data:
        write_to_file(fng_data, "market_sentiment_history.json")
    
    # 3. Fetch and write Market Breadth/Fund Flows (Historical data for trend)
    market_data_history = fetch_market_data_for_trend()
    if market_data_history:
        write_to_file(market_data_history, "market_data_history.json")

    # 4. Fetch and write Money Fund data (Latest data only)
    money_fund_data = fetch_money_fund_data()
    if money_fund_data:
        write_to_file(money_fund_data, "money_fund_data.json")
    
    print("Data synchronization process finished.")

if __name__ == "__main__":
    main()
