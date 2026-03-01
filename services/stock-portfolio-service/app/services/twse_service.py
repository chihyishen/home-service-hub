import requests
import time
import logging
from typing import Dict, Optional, List
from decimal import Decimal
from ..tracing import tracer

logger = logging.getLogger(__name__)

class TWSEapiError(Exception):
    pass

def get_stock_quotes(symbols: List[str]) -> Dict[str, Dict]:
    """
    獲取多檔股票的即時報價
    TWSE API: https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_2330.tw|tse_2317.tw
    """
    if not symbols:
        return {}

    # 確保 symbol 是乾淨的數字 (對外呼叫前最後確認)
    clean_symbols = [s.split('.')[0].upper() for s in symbols]

    # 組合查詢參數, 預設先試 tse (證交所), 如果沒試到可以擴充 otc (櫃買)
    # 這裡簡單處理，全部嘗試 tse 和 otc
    ch_list = []
    for s in clean_symbols:
        ch_list.append(f"tse_{s}.tw")
        ch_list.append(f"otc_{s}.tw")
    
    ex_ch = "|".join(ch_list)
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex_ch}&_={int(time.time() * 1000)}"

    try:
        with tracer.start_as_current_span("fetch_twse_quotes") as span:
            span.set_attribute("stock.symbols", clean_symbols)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "msgArray" not in data:
                logger.warning(f"TWSE API 回傳格式不正確: {data}")
                return {}

            results = {}
            for item in data["msgArray"]:
                symbol = item.get("c") # 股票代碼
                current_price = item.get("z") # 最近成交價
                yesterday_close = item.get("y") # 昨收價
                
                if current_price == "-": # 有可能剛開盤或是盤後沒成交
                    current_price = yesterday_close
                
                try:
                    price_val = Decimal(str(current_price))
                except (TypeError, ValueError):
                    price_val = Decimal("0.0")
                
                try:
                    y_close_val = Decimal(str(yesterday_close))
                except (TypeError, ValueError):
                    y_close_val = price_val # 如果拿不到昨收，就用當前價代替 (change = 0)

                results[symbol] = {
                    "symbol": symbol,
                    "name": item.get("n"),
                    "current_price": price_val,
                    "yesterday_close": y_close_val,
                    "time": item.get("t")
                }
            
            span.set_attribute("twse.results_count", len(results))
            return results

    except Exception as e:
        logger.error(f"呼叫 TWSE API 失敗: {str(e)}")
        return {}
