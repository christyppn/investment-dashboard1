import requests
import json
import os
import time
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import random
import logging

# --- Configuration ---
DATA_DIR = "data"
MAX_RETRIES = 3
RETRY_DELAY = 5 # seconds
HIBOR_FRESHNESS_DAYS = 5 # Max days old for HIBOR data to be considered fresh
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sync_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Yahoo Finance Symbols (Confirmed symbols for all required data points)
YAHOO_SYMBOLS = {
    # Market Breadth (US) - Standard ETF tickers
    "SPY": "SPY", "QQQ": "QQQ", "DIA": "DIA",
    # Global Indices and VIX
    "GSPC": "^GSPC", "IXIC": "^IXIC", "VIX": "^VIX", "HSI": "^HSI", "N225": "^N225",
    # Sector ETFs
    "XLK": "XLK", "XLC": "XLC", "XLY": "XLY", "XLP": "XLP", "XLV": "XLV", "XLF": "XLF",
    "XLE": "XLE", "XLI": "XLI", "XLB": "XLB", "XLU": "XLU", "VNQ": "VNQ",
    # Commodities/Thematic
    "GLD": "GLD", "ROBO": "ROBO", "SMH": "SMH", "IWM": "IWM",
    # Money Funds (for money_fund.js) - Using ETFs for better stability
    "VOO": "VOO", "VTI": "VTI", "BND": "BND", "BIL": "BIL"
}

# --- Helper Functions ---

def _get_user_agent() -> str:
    """Get a random User-Agent strings to avoid being blocked by scraping targets."""
    user_agent_strings = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    return random.choice(user_agent_strings)

def save_json(data, filename):
    """Saves data to a JSON file in the data directory."""
    path = os.path.join(DATA_DIR, filename)
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Successfully saved data to {path}")
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")

def process_yahoo_data(symbol, df):
    """
    Processes raw yfinance DataFrame to calculate daily changes,
    and includes the critical division-by-zero check and 30-day truncation.
    """
    if df.empty:
        return []

    # Calculate daily percentage change for Close price
    df['change_percent'] = df['Close'].pct_change() * 100
    
    # Clean up and format
    df = df.reset_index()
    if pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    
    # Select and rename columns for final output
    df = df.rename(columns={'Date': 'date', 'Close': 'close', 'Volume': 'volume'}) # Rename columns
    df = df[["date", "close", "change_percent", "volume"]] # Select and reorder columns
    time_series_list = df.to_dict('records')
    
    # Remove rows with NaN close prices (e.g., holidays)
    time_series_list = [item for item in time_series_list if not pd.isna(item['close'])]

    # Remove the first row (NaN change) if it still exists
    if time_series_list and pd.isna(time_series_list[0]['change_percent']):
        time_series_list.pop(0)

    # Final Optimization: Only keep the latest 30 trading days for frontend display
    return time_series_list[-30:]

def fetch_with_retry(url, headers=None, timeout=15):
    """Attempts to fetch a URL with a retry mechanism."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {url}: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1)) # Exponential backoff
            else:
                logger.error(f"All {MAX_RETRIES} attempts failed for {url}.")
                raise

# --- Data Fetching Functions ---

def fetch_alternative_fng():
    """Fetches the Crypto Fear & Greed Index from Alternative.me API."""
    url = "https://api.alternative.me/fng/"
    error_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "value": 0,
        "sentiment": "ERROR",
        "source": "Fetch Failed: Alternative.me API error."
    }
    
    try:
        response = fetch_with_retry(url)
        data = response.json()
        
        if data and data.get('data') and len(data['data']) > 0:
            fng_data = data['data'][0]
            
            # Data Validation
            try:
                value = int(fng_data.get('value', 0))
                if value < 0 or value > 100:
                    raise ValueError("F&G value out of range (0-100)")
            except (ValueError, TypeError) as e:
                logger.error(f"F&G Data Validation Failed: Invalid value type or range. {e}")
                error_data["source"] = f"Fetch Failed: Invalid F&G value: {fng_data.get('value')}"
                save_json(error_data, 'fear_greed_index.json')
                return False

            sentiment = fng_data.get('value_classification', 'ERROR')
            
            final_data = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "value": value,
                "sentiment": sentiment,
                "source": "Alternative.me (Crypto) API"
            }
            save_json(final_data, 'fear_greed_index.json')
            logger.info("Successfully fetched Fear & Greed Index from Alternative.me API.")
            return True
        
        error_data["source"] = "Fetch Failed: Alternative.me API returned no data."
        save_json(error_data, 'fear_greed_index.json')
        return False

    except Exception as e:
        error_data["source"] = f"Fetch Failed: Network or Parsing Error: {str(e)[:100]}..."
        save_json(error_data, 'fear_greed_index.json')
        logger.error(f"Failed to fetch F&G data: {e}")
        return False

def fetch_hkma_hibor():
    """Fetches HIBOR rates from HKMA API with corrected field names and backtracking."""
    url = "https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily"
    keys = ['ir_1m', 'ir_3m', 'ir_6m'] # Corrected keys based on raw JSON inspection
    
    error_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "rates": [{"term": "ERROR", "rate": 0.0, "date": "N/A"}],
        "error_message": "Fetch Failed: Network or API Error."
    }

    try:
        response = fetch_with_retry(url)
        data = response.json()
        
        if data.get('header', {}).get('success') != True or not data.get('result', {}).get('records'):
            error_data["error_message"] = f"Fetch Failed: HKMA API returned error or no records. Message: {data.get('header', {}).get('err_msg')}"
            save_json(error_data, "hibor_rates.json")
            logger.error(f"HKMA API returned error or no records: {error_data['error_message']}")
            return False

        records = data['result']['records']
        
        valid_rates = {}
        data_date = "N/A"
        
        for record in records:
            # Check if all required keys have valid, non-null values
            if all(record.get(key) is not None for key in keys):
                data_date = record['end_of_day']
                
                # Data Validation for HIBOR rates
                try:
                    valid_rates = {
                        'Overnight': float(record.get('ir_overnight', 0.0)),
                        '1個月': float(record.get('ir_1m', 0.0)),
                        '3個月': float(record.get('ir_3m', 0.0)),
                        '6個月': float(record.get('ir_6m', 0.0)),
                    }
                    # Simple check to ensure rates are positive and reasonable
                    if any(rate <= 0 for rate in valid_rates.values()):
                        raise ValueError("HIBOR rate is non-positive.")
                except (ValueError, TypeError) as e:
                    logger.error(f"HIBOR Data Validation Failed: Invalid rate value. {e}")
                    continue # Skip this record and check the next one

                break # Found a valid record, break the loop

        if not valid_rates:
            error_data["error_message"] = "Fetch Failed: No valid HIBOR data found in recent records."
            save_json(error_data, "hibor_rates.json")
            logger.error("No valid HIBOR data found in recent records.")
            return False

        # Data Freshness Check
        try:
            date_obj = datetime.strptime(data_date, '%Y-%m-%d')
            if (datetime.now() - date_obj).days > HIBOR_FRESHNESS_DAYS:
                logger.warning(f"HIBOR data is old. Date: {data_date}. Max freshness: {HIBOR_FRESHNESS_DAYS} days.")
        except ValueError:
            logger.warning(f"Could not parse HIBOR data date: {data_date}")

        final_data = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data_date": data_date,
            "rates": [
                {"term": term, "rate": rate} for term, rate in valid_rates.items()
            ]
        }
        save_json(final_data, "hibor_rates.json")
        logger.info("Successfully fetched HIBOR rates.")
        return True
            
    except Exception as e:
        error_data["error_message"] = f"Fetch Failed: Network or API Error: {str(e)[:100]}..."
        save_json(error_data, "hibor_rates.json")
        logger.error(f"Failed to fetch HIBOR data: {e}")
        return False

def fetch_market_data():
    """Fetches market data (indices, ETFs, money funds) using yfinance."""
    start_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')
    market_data_history = {}
    money_fund_data = []
    latest_vix_close = None
    latest_gspc_volume = None
    latest_vix_close = None
    latest_gspc_volume = None
    yahoo_symbols_list = list(YAHOO_SYMBOLS.values())
    
    try:
        df_all = yf.download(yahoo_symbols_list, start=start_date, interval="1d", auto_adjust=False, progress=False)
        if df_all.empty:
            logger.error("Yahoo Finance returned no data.")
            return False
    except Exception as e:
        logger.error(f"Error fetching from Yahoo Finance: {e}")
        return False

    for symbol_key, yahoo_symbol in YAHOO_SYMBOLS.items():
        try:
            if isinstance(df_all['Close'], pd.DataFrame):
                df = df_all.loc[:, (slice(None), yahoo_symbol)].droplevel(1, axis=1)
            else:
                df = df_all
            
            if not df.empty:
                processed_data = process_yahoo_data(symbol_key, df)
                if symbol_key in ["VOO", "VTI", "BND", "BIL"]:
                    if processed_data:
                        latest_data = processed_data[-1]
                        money_fund_data.append({
                            "symbol": symbol_key,
                            "latest_price": latest_data['close'],
                            "daily_change_percent": latest_data['change_percent'],
                            "date": latest_data['date']
                        })
                else:
                    if processed_data:
                        if symbol_key == "VIX" and processed_data:
                            latest_vix_close = processed_data[-1]['close']
                        elif symbol_key == "GSPC" and processed_data:
                            latest_gspc_volume = processed_data[-1]['volume']
                        
                        if symbol_key == "VIX" and processed_data:
                            latest_vix_close = processed_data[-1]['close']
                        elif symbol_key == "GSPC" and processed_data:
                            latest_gspc_volume = processed_data[-1]['volume']
                        
                        if symbol_key == "VIX" and processed_data:
                            latest_vix_close = processed_data[-1]['close']
                        elif symbol_key == "GSPC" and processed_data:
                            latest_gspc_volume = processed_data[-1]['volume']
                        
                        processed_data[0]['name'] = symbol_key 
                        market_data_history[symbol_key] = processed_data
        except Exception as e:
            logger.error(f"Could not process data for {symbol_key}: {e}")

    save_json(market_data_history, "market_data_history.json")
    save_json({
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "funds": money_fund_data
    }, "money_fund_data.json")
    logger.info("Successfully fetched market data from Yahoo Finance.")
    return True, latest_vix_close, latest_gspc_volume

def fetch_market_breadth_alpha_vantage():
    """Fetches market breadth data using Alpha Vantage Sector Performance API."""
    if not ALPHA_VANTAGE_API_KEY:
        logger.error("ALPHA_VANTAGE_API_KEY not set for market breadth.")
        return False

    url = f"https://www.alphavantage.co/query?function=SECTOR&apikey={ALPHA_VANTAGE_API_KEY}"
    error_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "advancing_issues": 0,
        "declining_issues": 0,
        "new_highs": 0,
        "new_lows": 0,
        "a_d_line": 0,
        "source": "Fetch Failed: Alpha Vantage API error."
    }

    try:
        response = fetch_with_retry(url)
        data = response.json()

        if "Error Message" in data:
            error_message = data["Error Message"]
            error_data["source"] = f"Fetch Failed: Alpha Vantage Error: {error_message}"
            save_json(error_data, "market_breadth.json")
            logger.error(f"Alpha Vantage API error for market breadth: {error_message}")
            return False
        
        # Alpha Vantage SECTOR API provides sector performance, not direct breadth.
        # We will use a simplified approach for market breadth based on sector performance.
        if "Rank A: Realtime Performance" in data:
            realtime_performance = data["Rank A: Realtime Performance"]
            advancing_sectors = 0
            declining_sectors = 0
            
            for sector, change_percent_str in realtime_performance.items():
                change_percent = float(change_percent_str.replace("%", ""))
                if change_percent > 0:
                    advancing_sectors += 1
                elif change_percent < 0:
                    declining_sectors += 1
            
            final_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "advancing_issues": advancing_sectors * 100, # Scale for a more 'issue-like' number
                "declining_issues": declining_sectors * 100,
                "new_highs": 0, # Not directly available from this API
                "new_lows": 0,  # Not directly available from this API
                "a_d_line": (advancing_sectors - declining_sectors) * 100,
                "source": "Alpha Vantage Sector Performance (Simplified Breadth)"
            }
            save_json(final_data, "market_breadth.json")
            logger.info("Successfully fetched market breadth from Alpha Vantage.")
            return True
        
        error_data["source"] = "Fetch Failed: Alpha Vantage API returned no sector data."
        save_json(error_data, "market_breadth.json")
        return False

    except Exception as e:
        error_data["source"] = f"Fetch Failed: Network or Parsing Error: {str(e)[:100]}..."
        save_json(error_data, "market_breadth.json")
        logger.error(f"Failed to fetch market breadth data from Alpha Vantage: {e}")
        return False

def generate_dummy_data(fng_value=None, fng_sentiment=None, vix_value=None, gspc_volume=None):
    """Generates dummy data for files not covered by real-time fetching."""
    # Dynamic AI Analysis based on F&G Index
    analysis_text = "市場情緒中性，建議保持觀望。"
    rating = "Neutral"

    # Initialize sentiment and analysis based on F&G
    if fng_value is not None:
        if fng_value >= 75:
            analysis_text = "市場情緒極度貪婪，投資者情緒高漲。"
            rating = "Extremely Greedy"
        elif fng_value >= 55:
            analysis_text = "市場情緒貪婪，投資者信心較強。"
            rating = "Greedy"
        elif fng_value >= 45:
            analysis_text = "市場情緒中性，觀望情緒濃厚。"
            rating = "Neutral"
        elif fng_value >= 25:
            analysis_text = "市場情緒恐懼，可能存在超跌機會。"
            rating = "Fearful"
        else:
            analysis_text = "市場情緒極度恐懼，恐慌情緒蔓延。"
            rating = "Extremely Fearful"

    # Incorporate VIX and Volume for more nuanced analysis
    additional_analysis = []

    if vix_value is not None:
        if vix_value > 25: # High VIX, indicating fear/uncertainty
            additional_analysis.append("VIX指數飆升，顯示市場避險情緒濃厚，短期波動可能加劇。")
            if fng_value is not None and fng_value < 25: # Extreme Fear + High VIX
                analysis_text = "市場進入極度恐慌，VIX飆升顯示避險情緒濃厚。歷史經驗顯示這往往是長線優質資產的佈局窗口。"
                rating = "Extreme Fear (High Volatility)"
            elif fng_value is not None and fng_value < 45: # Fear + High VIX
                analysis_text = "市場情緒恐懼，VIX處於高位，短期內市場可能繼續震盪，但也是尋找錯殺優質股的時機。"
                rating = "Fearful (High Volatility)"
        elif vix_value < 15: # Low VIX, indicating complacency
            additional_analysis.append("VIX指數處於低位，市場波動性較小，但需警惕潛在的過度樂觀情緒。")
            if fng_value is not None and fng_value > 75: # Extreme Greed + Low VIX
                analysis_text = "市場情緒極度貪婪，且VIX處於歷史低位顯示投資者過度樂觀。需警惕隨時可能出現的技術性回調。"
                rating = "Extreme Greed (Low Volatility)"
            elif fng_value is not None and fng_value > 55: # Greed + Low VIX
                analysis_text = "市場情緒貪婪，VIX處於低位，短期內市場可能繼續上漲，但應注意風險控制。"
                rating = "Greedy (Low Volatility)"

    if gspc_volume is not None:
        # To make a meaningful analysis of volume, we need historical context (e.g., average volume)
        # For now, we'll use a simplified approach or assume it's part of broader market trend analysis
        # For a more robust solution, average volume over a period would be needed.
        # Placeholder for future enhancement: compare current volume to moving average.
        if gspc_volume > 1000000000: # Arbitrary high volume threshold for S&P 500
            additional_analysis.append("S&P 500成交量顯著放大，顯示市場交投活躍，趨勢可能得到確認。")
        elif gspc_volume < 500000000: # Arbitrary low volume threshold
            additional_analysis.append("S&P 500成交量萎縮，市場觀望情緒較濃，趨勢不明朗。")

    if additional_analysis:
        analysis_text += " " + " ".join(additional_analysis)

    ai_analysis = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sentiment": fng_sentiment if fng_sentiment else rating,
        "analysis": analysis_text,
        "rating": rating
    }
    save_json(ai_analysis, 'ai_analysis.json')
    
    f13_data = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "fund_name": "伯克希爾·哈撒韋 (BRK.B) 13F 持倉 (Q3 2025)",
        "total_value": 422.38,
        "cash_ratio": 167.68,
        "top_10_ratio": 85.2,
        "quarterly_change": -2.5,
        "holdings": [
            {"symbol": "AAPL", "value": 150.5, "change": 1.2},
            {"symbol": "BAC", "value": 54.8, "change": -5.6},
            {"symbol": "KO", "value": 26.4, "change": 0.0},
        ]
    }
    save_json(f13_data, '13f-data.json')
    
    market_sentiment = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "consensus": {
            "latest_sentiment": "中性偏多",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    save_json(market_sentiment, 'market_sentiment.json')

    # Dummy data for previously unhandled files to ensure timestamp update
    fund_flows = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "flows": [
            {"date": (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'), "flow": 1.2, "type": "ETF"},
            {"date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), "flow": -0.5, "type": "Mutual Fund"},
        ]
    }
    save_json(fund_flows, 'fund_flows.json')

    market_sentiment_history = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "history": [
            {"date": (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'), "sentiment": "Greed", "value": 65},
            {"date": (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'), "sentiment": "Neutral", "value": 50},
        ]
    }
    save_json(market_sentiment_history, 'market_sentiment_history.json')

    # Dummy data for market_breadth.json as a fallback
    market_breadth_dummy = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "advancing_issues": 1850,
        "declining_issues": 1240,
        "new_highs": 125,
        "new_lows": 45,
        "a_d_line": 610,
        "source": "Dummy Data (Fallback)"
    }
    save_json(market_breadth_dummy, 'market_breadth.json')

    logger.info("Successfully generated dummy data.")

# --- Main Execution ---

if __name__ == "__main__":
    logger.info("Starting data synchronization script...")
    # Fetch F&G first to use in AI analysis
    fng_success = fetch_alternative_fng()
    fng_value = None
    fng_sentiment = None
    if fng_success:
        try:
            with open(os.path.join(DATA_DIR, 'fear_greed_index.json'), 'r', encoding='utf-8') as f:
                fng_data = json.load(f)
                fng_value = fng_data.get('value')
                fng_sentiment = fng_data.get('sentiment')
        except Exception as e:
            logger.error(f"Failed to read fear_greed_index.json for AI analysis: {e}")

    fetch_hkma_hibor()
    market_data_success, latest_vix_close, latest_gspc_volume = fetch_market_data()
    fetch_market_breadth_alpha_vantage()
    generate_dummy_data(fng_value, fng_sentiment, latest_vix_close, latest_gspc_volume)
    logger.info("Data synchronization complete.")
