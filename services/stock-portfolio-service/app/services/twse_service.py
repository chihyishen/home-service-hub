import requests
import time
import logging
import json
import os
from typing import Dict, List
from decimal import Decimal, InvalidOperation
from ..tracing import tracer

logger = logging.getLogger(__name__)

class TWSEapiError(Exception):
    pass


def _bool_env(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _fetch_twse_response(url: str) -> requests.Response:
    """
    優先使用憑證驗證；若憑證鏈異常導致 SSL 失敗，降級重試一次 verify=False。
    可透過 TWSE_SSL_VERIFY=false 直接關閉驗證。
    """
    verify_ssl = _bool_env("TWSE_SSL_VERIFY", True)
    try:
        return requests.get(url, timeout=10, verify=verify_ssl)
    except requests.exceptions.SSLError:
        if not verify_ssl:
            raise
        logger.warning("TWSE SSL 驗證失敗，改用 verify=False 重試一次")
        return requests.get(url, timeout=10, verify=False)


def _parse_twse_json(raw_text: str) -> Dict:
    """
    解析 TWSE 回傳字串，容忍 BOM/前後雜訊/JSONP 包裹。
    """
    text = (raw_text or "").strip()
    if not text:
        return {}

    # 移除 UTF-8 BOM
    text = text.lstrip("\ufeff")

    # 若回傳包含前後雜訊或 JSONP，抓第一個 { 到最後一個 }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace == -1 or last_brace == -1 or first_brace > last_brace:
        raise TWSEapiError("TWSE 回傳非 JSON 格式內容")
    candidate = text[first_brace:last_brace + 1]

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise TWSEapiError(f"TWSE JSON 解析失敗: {exc}") from exc

    if not isinstance(parsed, dict):
        raise TWSEapiError("TWSE JSON 根節點不是物件")

    return parsed

def get_stock_quotes(symbols: List[str]) -> Dict[str, Dict]:
    """
    獲取多檔股票的即時報價
    """
    if not symbols:
        return {}

    # 預處理代碼，轉大寫並去除後綴
    clean_symbols = [s.split('.')[0].upper().strip() for s in symbols]

    ch_list = []
    for s in clean_symbols:
        ch_list.append(f"tse_{s}.tw")
        ch_list.append(f"otc_{s}.tw")
    
    ex_ch = "|".join(ch_list)
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex_ch}&_={int(time.time() * 1000)}"

    try:
        with tracer.start_as_current_span("fetch_twse_quotes") as span:
            span.set_attribute("stock.symbols", clean_symbols)
            response = _fetch_twse_response(url)
            response.raise_for_status()
            raw_text = response.text
            try:
                data = _parse_twse_json(raw_text)
            except TWSEapiError:
                logger.error("TWSE 回傳解析失敗，raw prefix=%r", raw_text[:300])
                raise

            msg_array = data.get("msgArray")
            if not isinstance(msg_array, list) or not msg_array:
                logger.warning(f"TWSE API 未回傳任何股票數據: {data}")
                return {}

            results = {}
            
            def to_decimal(val) -> Decimal:
                if val is None or val == "" or val == "-":
                    return Decimal("0.0")
                try:
                    return Decimal(str(val).replace(",", ""))
                except (TypeError, ValueError, InvalidOperation):
                    return Decimal("0.0")

            for item in msg_array:
                if not isinstance(item, dict):
                    continue
                symbol = item.get("c", "").strip()
                if not symbol:
                    continue
                
                # 取得各項價格欄位
                z = item.get("z") # 成交
                pz = item.get("pz") # 試算
                y = item.get("y") # 昨收
                
                price_val = to_decimal(z)
                if price_val == 0: price_val = to_decimal(pz)
                if price_val == 0: price_val = to_decimal(y)
                
                y_close_val = to_decimal(y)
                if y_close_val == 0: y_close_val = price_val

                # 確保不被空數據覆蓋，且匹配原始請求的 symbol
                if symbol in clean_symbols:
                    if symbol not in results or price_val > 0:
                        results[symbol] = {
                            "symbol": symbol,
                            "name": item.get("n"),
                            "current_price": price_val,
                            "yesterday_close": y_close_val,
                            "time": item.get("t") or item.get("%")
                        }
                        logger.info(f"成功解析: {symbol}, 價格: {price_val}")
            
            return results

    except Exception as e:
        logger.error(f"呼叫 TWSE API 失敗: {str(e)}", exc_info=True)
        return {}
