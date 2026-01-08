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
RETRY_DELAY = 5  # seconds
HIBOR_FRESHNESS_DAYS = 5  # Max days old for HIBOR data to be considered fresh

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
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
    # Money Funds (for money_fund.js)
    "VFIAX": "VFIAX", "VTSAX": "VTSAX", "VBTLX": "VBTLX", "BIL": "BIL"
}

# --- Helper Functions ---


def _get_user_agent() -> str:
    """Get a random User-Agent string to avoid being blocked by scraping targets."""
    user_agent_strings = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    return random.choice(user_agent_strings)


def save_json(data, filename):
    """Saves data to a JSON file in the data directory."""
    path = os.path.join(DATA_DIR, filename)
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"Successfully saved data to {path}")
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")


def process_yahoo_data(symbol, df):
    """
    Processes raw yfinance DataFrame to calculate daily changes and
    returns the latest 30 trading days as list of dicts.
    """
    if df.empty:
        return []

    df["change_percent"] = df["Close"].pct_change() * 100
    df = df.reset_index()

    if pd.api.types.is_datetime64_any_dtype(df["Date"]):
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

    df = df.rename(columns={"Date": "date", "Close": "close"})
    df = df[["date", "close", "change_percent"]]

    time_series_list = df.to_dict("records")

    if time_series_list:
        time_series_list.pop(0)

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
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                logger.error(f"All {MAX_RETRIES} attempts failed for {url}.")
                raise

# --- Data Fetching Functions ---


def fetch_alternative_fng():
    """Fetches the Crypto Fear & Greed Index from Alternative.me API."""
    url = "https://api.alternative.me/fng/"
    error_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "value": 0,
        "sentiment": "ERROR",
        "source": "Fetch Failed: Alternative.me API error.",
    }

    try:
        response = fetch_with_retry(url)
        data = response.json()

        if data and data.get("data") and len(data["data"]) > 0:
            fng_data = data["data"][0]

            try:
                value = int(fng_data.get("value", 0))
                if value < 0 or value > 100:
                    raise ValueError("F&G value out of range (0-100)")
            except (ValueError, TypeError) as e:
                logger.error(f"F&G Data Validation Failed: {e}")
                error_data["source"] = (
                    f"Fetch Failed: Invalid F&G value: {fng_data.get('value')}"
                )
                save_json(error_data, "fear_greed_index.json")
                return False

            sentiment = fng_data.get("value_classification", "ERROR")
            final_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "value": value,
                "sentiment": sentiment,
                "source": "Alternative.me (Crypto) API",
            }

            save_json(final_data, "fear_greed_index.json")
            logger.info("Successfully fetched Fear & Greed Index from Alternative.me API.")
            return True

        error_data["source"] = "Fetch Failed: Alternative.me API returned no data."
        save_json(error_data, "fear_greed_index.json")
        return False

    except Exception as e:
        error_data["source"] = (
            f"Fetch Failed: Network or Parsing Error: {str(e)[:100]}..."
        )
        save_json(error_data, "fear_greed_index.json")
        logger.error(f"Failed to fetch F&G data: {e}")
        return False


def fetch_hkma_hibor():
    """Fetches HIBOR rates from HKMA API with field validation."""
    url = (
        "https://api.hkma.gov.hk/public/market-data-and-statistics/"
        "monthly-statistical-bulletin/er-ir/hk-interbank-ir-daily"
    )
    keys = ["ir_1m", "ir_3m", "ir_6m"]

    error_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rates": [{"term": "ERROR", "rate": 0.0, "date": "N/A"}],
        "error_message": "Fetch Failed: Network or API Error.",
    }

    try:
        response = fetch_with_retry(url)
        data = response.json()

        if (
            data.get("header", {}).get("success") is not True
            or not data.get("result", {}).get("records")
        ):
            error_data["error_message"] = (
                "Fetch Failed: HKMA API returned error or no records. "
                f"Message: {data.get('header', {}).get('err_msg')}"
            )
            save_json(error_data, "hibor_rates.json")
            logger.error(error_data["error_message"])
            return False

        records = data["result"]["records"]
        valid_rates = {}
        data_date = "N/A"

        for record in records:
            if all(record.get(key) is not None for key in keys):
                data_date = record["end_of_day"]
                try:
                    valid_rates = {
                        "Overnight": float(record.get("ir_overnight", 0.0)),
                        "1個月": float(record.get("ir_1m", 0.0)),
                        "3個月": float(record.get("ir_3m", 0.0)),
                        "6個月": float(record.get("ir_6m", 0.0)),
                    }
                    if any(rate <= 0 for rate in valid_rates.values()):
                        raise ValueError("HIBOR rate is non-positive.")
                except (ValueError, TypeError) as e:
                    logger.error(f"HIBOR Data Validation Failed: {e}")
                    continue
                break

        if not valid_rates:
            error_data["error_message"] = (
                "Fetch Failed: No valid HIBOR data found in recent records."
            )
            save_json(error_data, "hibor_rates.json")
            logger.error(error_data["error_message"])
            return False

        try:
            date_obj = datetime.strptime(data_date, "%Y-%m-%d")
            if (datetime.now() - date_obj).days > HIBOR_FRESHNESS_DAYS:
                logger.warning(
                    f"HIBOR data is old. Date: {data_date}. "
                    f"Max freshness: {HIBOR_FRESHNESS_DAYS} days."
                )
        except ValueError:
            logger.warning(f"Could not parse HIBOR data date: {data_date}")

        final_data = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_date": data_date,
            "rates": [{"term": term, "rate": rate} for term, rate in valid_rates.items()],
        }

        save_json(final_data, "hibor_rates.json")
        logger.info("Successfully fetched HIBOR rates.")
        return True

    except Exception as e:
        error_data["error_message"] = (
            f"Fetch Failed: Network or API Error: {str(e)[:100]}..."
        )
        save_json(error_data, "hibor_rates.json")
        logger.error(f"Failed to fetch HIBOR data: {e}")
        return False


def fetch_market_data():
    """Fetches market data (indices, ETFs, money funds) using yfinance."""
    start_date = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")

    market_data_history = {}
    money_fund_data = []
    yahoo_symbols_list = list(YAHOO_SYMBOLS.values())

    try:
        df_all = yf.download(
            yahoo_symbols_list,
            start=start_date,
            interval="1d",
            auto_adjust=False,
            progress=False,
        )
        if df_all.empty:
            logger.error("Yahoo Finance returned no data.")
            return False
    except Exception as e:
        logger.error(f"Error fetching from Yahoo Finance: {e}")
        return False

    for symbol_key, yahoo_symbol in YAHOO_SYMBOLS.items():
        try:
            if isinstance(df_all["Close"], pd.DataFrame):
                df = df_all.loc[:, (slice(None), yahoo_symbol)].droplevel(1, axis=1)
            else:
                df = df_all

            if not df.empty:
                processed_data = process_yahoo_data(symbol_key, df)

                if symbol_key in ["VFIAX", "VTSAX", "VBTLX", "BIL"]:
                    if processed_data:
                        latest_data = processed_data[-1]
                        money_fund_data.append(
                            {
                                "symbol": symbol_key,
                                "latest_price": latest_data["close"],
                                "daily_change_percent": latest_data["change_percent"],
                                "date": latest_data["date"],
                            }
                        )
                else:
                    if processed_data:
                        processed_data[0]["name"] = symbol_key
                        market_data_history[symbol_key] = processed_data

        except Exception as e:
            logger.error(f"Could not process data for {symbol_key}: {e}")

    save_json(market_data_history, "market_data_history.json")
    save_json(
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "funds": money_fund_data,
        },
        "money_fund_data.json",
    )
    logger.info("Successfully fetched market data from Yahoo Finance.")
    return True

# --- New automated data for 3 JSON files ---


def fetch_fund_flows_from_alpha():
    """
    Approximate 'fund flows' using weekly volume and price of major ETFs
    from Alpha Vantage. This is a proxy, not official EPFR-style flow data.
    """
    if not ALPHA_VANTAGE_API_KEY:
        logger.error("ALPHA_VANTAGE_API_KEY not set; skip fund flows.")
        return False

    etfs = ["SPY", "QQQ", "IWM"]
    base_url = "https://www.alphavantage.co/query"
    flows = []

    for symbol in etfs:
        params = {
            "function": "TIME_SERIES_WEEKLY",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_API_KEY,
        }
        try:
            resp = requests.get(base_url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            ts = data.get("Weekly Time Series") or data.get("Time Series (Weekly)", {})
            if not ts:
                logger.warning(f"No weekly data for {symbol} from Alpha Vantage.")
                continue

            dates = sorted(ts.keys(), reverse=True)[:2]
            if len(dates) < 2:
                continue
            d0, d1 = dates[0], dates[1]
            v0 = float(ts[d0]["5. volume"])
            c0 = float(ts[d0]["4. close"])
            v1 = float(ts[d1]["5. volume"])
            c1 = float(ts[d1]["4. close"])

            flow_proxy = (v0 * c0 - v1 * c1) / 1e9  # USD bn
            flows.append(
                {
                    "symbol": symbol,
                    "latest_week": d0,
                    "prev_week": d1,
                    "flow_proxy_usd_bn": round(flow_proxy, 2),
                }
            )
        except Exception as e:
            logger.error(f"Error fetching fund flows proxy for {symbol}: {e}")

    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method": "Alpha Vantage weekly price*volume proxy, not official flow data.",
        "flows": flows,
    }
    save_json(result, "fund_flows.json")
    return True


def fetch_market_breadth_from_finnhub():
    """
    Fetch simple market breadth numbers using Finnhub index constituents.
    Approximates advancers/decliners by comparing latest price vs previous close.
    """
    if not FINNHUB_API_KEY:
        logger.error("FINNHUB_API_KEY not set; skip market breadth.")
        return False

    index_symbols = {
        "sp500": "^GSPC",
        "nasdaq100": "^NDX",
    }
    base_const = "https://finnhub.io/api/v1/index/constituents"
    base_quote = "https://finnhub.io/api/v1/quote"

    breadth = {}

    for name, idx in index_symbols.items():
        try:
            const_resp = fetch_with_retry(
                f"{base_const}?symbol={idx}&token={FINNHUB_API_KEY}", timeout=20
            )
            symbols = const_resp.json().get("constituents", [])
            adv = dec = unch = 0

            for s in symbols[:200]:  # cap for rate limits
                q_resp = fetch_with_retry(
                    f"{base_quote}?symbol={s}&token={FINNHUB_API_KEY}", timeout=10
                )
                q = q_resp.json()
                c = q.get("c")
                pc = q.get("pc")
                if c is None or pc is None:
                    continue
                if c > pc:
                    adv += 1
                elif c < pc:
                    dec += 1
                else:
                    unch += 1

            breadth[name] = {
                "advancers": adv,
                "decliners": dec,
                "unchanged": unch,
                "sample_size": min(len(symbols), 200),
            }
        except Exception as e:
            logger.error(f"Error fetching breadth for {name}: {e}")

    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "advance_decline": breadth,
    }
    save_json(result, "market_breadth.json")
    return True


def fetch_sentiment_history_from_finnhub():
    """
    Build a simple sentiment history using Finnhub news sentiment for SPY.
    """
    if not FINNHUB_API_KEY:
        logger.error("FINNHUB_API_KEY not set; skip sentiment history.")
        return False

    end = datetime.utcnow().date()
    start = end - timedelta(days=30)
    url = (
        "https://finnhub.io/api/v1/news-sentiment"
        f"?symbol=SPY&from={start}&to={end}&token={FINNHUB_API_KEY}"
    )
    try:
        resp = fetch_with_retry(url, timeout=20)
        data = resp.json()
        daily = data.get("sentiment", {})
    except Exception as e:
        logger.error(f"Error fetching sentiment history: {e}")
        daily = {}

    history = []
    for d, v in sorted(daily.items()):
        score = v.get("normalized", 0)
        if score > 0.2:
            label = "樂觀"
        elif score > 0.0:
            label = "中性偏多"
        elif score < -0.2:
            label = "偏淡"
        else:
            label = "中性"
        history.append({"date": d, "sentiment": label, "score": score})

    result = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "history": history,
    }
    save_json(result, "market_sentiment_history.json")
    return True

# --- Dummy data still used for AI analysis / 13F / latest sentiment ---


def generate_dummy_data():
    """Generates dummy data for files not covered by real-time fetching."""
    ai_analysis = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sentiment": "Bullish",
        "analysis": (
            "市場情緒持續樂觀，主要指數在科技股帶動下創下新高。"
            "建議關注半導體和人工智能相關領域的長期投資機會。"
        ),
        "rating": "Bullish",
    }
    save_json(ai_analysis, "ai_analysis.json")

    f13_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fund_name": "伯克希爾·哈撒韋 (BRK.B) 13F 持倉 (Q3 2025)",
        "total_value": 422.38,
        "cash_ratio": 167.68,
        "top_10_ratio": 85.2,
        "quarterly_change": -2.5,
        "holdings": [
            {"symbol": "AAPL", "value": 150.5, "change": 1.2},
            {"symbol": "BAC", "value": 54.8, "change": -5.6},
            {"symbol": "KO", "value": 26.4, "change": 0.0},
        ],
    }
    save_json(f13_data, "13f-data.json")

    market_sentiment = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "consensus": {
            "latest_sentiment": "中性偏多",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    }
    save_json(market_sentiment, "market_sentiment.json")

    logger.info("Successfully generated dummy data.")

# --- Main Execution ---


if __name__ == "__main__":
    logger.info("Starting data synchronization script...")

    generate_dummy_data()
    fetch_alternative_fng()
    fetch_hkma_hibor()
    fetch_market_data()
    fetch_fund_flows_from_alpha()
    fetch_market_breadth_from_finnhub()
    fetch_sentiment_history_from_finnhub()

    logger.info("Data synchronization complete.")

