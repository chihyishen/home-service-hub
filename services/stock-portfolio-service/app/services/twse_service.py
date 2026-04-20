import requests
import time
import logging
import json
import os
from typing import Dict, List, Any
from decimal import Decimal, InvalidOperation
from shared_lib import get_tracer
tracer = get_tracer("stock-portfolio-service")

logger = logging.getLogger(__name__)

class TWSEapiError(Exception):
    pass

def _bool_env(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}

def _to_decimal(val: Any) -> Decimal:
    """
    安全轉換為 Decimal。
    針對 TWSE 的 'a' (買價) 或 'b' (賣價) 欄位，會自動拆分並取第一檔報價。
    """
    if val is None or val == "" or val == "-":
        return Decimal("0.0")
    try:
        # 處理多重報價格式，例如 "23.5900_23.6000_" -> 取 "23.5900"
        clean_val = str(val).split('_')[0].replace(",", "").strip()
        return Decimal(clean_val)
    except (TypeError, ValueError, InvalidOperation):
        return Decimal("0.0")

def fetch_raw_quotes(symbols: List[str]) -> Dict[str, Any]:
    """
    第一階段：發送網路請求並取得原始 JSON
    """
    if not symbols:
        return {}

    clean_symbols = [s.split('.')[0].upper().strip() for s in symbols]
    ch_list = [f"tse_{s}.tw|otc_{s}.tw" for s in clean_symbols]
    ex_ch = "|".join(ch_list)
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex_ch}&_={int(time.time() * 1000)}"
    
    # 預設跳過 SSL 驗證以提升內部服務發查穩定性
    verify_ssl = _bool_env("TWSE_SSL_VERIFY", False)

    with tracer.start_as_current_span("twse_network_request") as span:
        span.set_attribute("http.url", url)
        span.set_attribute("stock.symbols", clean_symbols)
        
        try:
            response = requests.get(url, timeout=10, verify=verify_ssl)
            response.raise_for_status()
            
            raw_text = response.text
            text = raw_text.lstrip("\ufeff").strip()
            
            # 偵測 JSON 邊界處理 BOM
            first_brace = text.find("{")
            last_brace = text.rfind("}")
            if first_brace == -1 or last_brace == -1:
                logger.error(f"TWSE 回傳格式異常: {text[:200]}")
                return {}
                
            return json.loads(text[first_brace:last_brace + 1])
            
        except Exception as e:
            logger.error(f"TWSE 網路請求失敗: {str(e)}")
            return {}

def parse_twse_msg_array(msg_array: List[Dict], target_symbols: List[str]) -> Dict[str, Dict]:
    """
    第二階段：從 msgArray 中解析出精確報價，支援成交價缺失時自動備援至五檔報價
    """
    results = {}
    clean_targets = [s.split('.')[0].upper().strip() for s in target_symbols]
    
    for item in msg_array:
        if not isinstance(item, dict):
            continue
            
        symbol = item.get("c", "").strip()
        if not symbol or symbol not in clean_targets:
            continue
            
        # 提取報價欄位
        z = item.get("z")   # 成交價
        pz = item.get("pz") # 試算成交價
        a = item.get("a")   # 最佳買盤價 (五檔)
        b = item.get("b")   # 最佳賣盤價 (五檔)
        y = item.get("y")   # 昨收價
        
        # 優先順序策略：成交 > 試算 > 買價 > 賣價 > 昨收
        price_val = _to_decimal(z)
        source = "z (成交)"
        
        if price_val == 0:
            price_val = _to_decimal(pz)
            source = "pz (試算)"
        if price_val == 0:
            price_val = _to_decimal(a)
            source = "a (最佳買入)"
        if price_val == 0:
            price_val = _to_decimal(b)
            source = "b (最佳賣出)"
        if price_val == 0:
            price_val = _to_decimal(y)
            source = "y (昨收)"
        
        y_close_val = _to_decimal(y)
        # 如果昨收也沒了，拿目前的價格當基準 (漲跌為 0)
        if y_close_val == 0:
            y_close_val = price_val

        # 寫入結果，若重複 symbol 則優先保留有報價的物件
        if symbol not in results or price_val > 0:
            results[symbol] = {
                "symbol": symbol,
                "name": item.get("n"),
                "current_price": price_val,
                "yesterday_close": y_close_val,
                "time": item.get("t") or item.get("%")
            }
            logger.info(f"解析股票 [{symbol}]: 價格={price_val}, 來源={source}, 昨收={y_close_val}")
            
    return results

def get_stock_quotes(symbols: List[str]) -> Dict[str, Dict]:
    """
    進入點：協調發查與解析
    """
    if not symbols:
        return {}
        
    with tracer.start_as_current_span("twse_get_quotes") as span:
        span.set_attribute("stock.request_symbols", symbols)
        
        raw_data = fetch_raw_quotes(symbols)
        msg_array = raw_data.get("msgArray", [])
        
        if not isinstance(msg_array, list) or not msg_array:
            logger.warning(f"TWSE 回傳資料為空或格式不正確: {symbols}")
            span.set_attribute("stock.result_count", 0)
            return {}
            
        results = parse_twse_msg_array(msg_array, symbols)
        span.set_attribute("stock.result_count", len(results))
        return results
