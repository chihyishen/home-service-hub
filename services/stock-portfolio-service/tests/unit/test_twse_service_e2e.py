import unittest
from decimal import Decimal
from unittest.mock import patch
import requests

from app.services.twse_service import _parse_twse_json, get_stock_quotes, _fetch_twse_response


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


SAMPLE_TWSE_JSON = """{"msgArray":[{"@":"0050.tw","tv":"3751","ps":"3751","nu":"http://www.yuantaetfs.com/#/RtNav/Index","pid":"9.tse.tw|1","pz":"81.1500","bp":"0","fv":"159","oa":"81.4000","ob":"81.3500","m%":"000000","key":"tse_0050.tw_20260226","^":"20260226","a":"81.2000_81.2500_81.3000_81.3500_81.4000_","b":"81.1500_81.1000_81.0500_81.0000_80.9500_","c":"0050","#":"13.tse.tw|1887","d":"20260226","%":"14:30:00","ch":"0050.tw","tlong":"1772087400000","ot":"14:30:00","f":"121_610_748_2670_3184_","g":"1085_2353_1131_4642_3459_","ip":"0","mt":"000000","ov":"105672","h":"81.5000","it":"02","oz":"81.3500","l":"80.8000","n":"元大台灣50","o":"81.2500","p":"0","ex":"tse","s":"3751","t":"13:30:00","u":"89.2000","v":"123548","w":"73.0000","nf":"元大台灣卓越50證券投資信託基金","y":"81.1000","z":"81.1500","ts":"0"},{"tv":"-","s":"-","c":"","z":"-"},{"@":"00919.tw","tv":"773","ps":"773","nu":"https://www.capitalfund.com.tw/etf/transaction/networth","pid":"9.tse.tw|142","pz":"24.6000","bp":"0","fv":"579","oa":"24.6000","ob":"24.5900","m%":"000000","^":"20260226","key":"tse_00919.tw_20260226","a":"24.6000_24.6100_24.6200_24.6300_24.6400_","b":"24.5900_24.5800_24.5700_24.5600_24.5500_","c":"00919","#":"13.tse.tw|2293","d":"20260226","%":"14:30:00","ch":"00919.tw","tlong":"1772087400000","ot":"14:30:00","f":"41_1286_1225_2105_3417_","g":"2220_1231_1372_1215_1926_","ip":"0","mt":"000000","ov":"36482","h":"24.6400","it":"02","oz":"24.6000","l":"24.2800","n":"群益台灣精選高息","o":"24.2800","p":"0","ex":"tse","s":"773","t":"13:30:00","u":"26.6900","v":"159025","w":"21.8500","nf":"群益台灣精選高息ETF證券投資信託基金","y":"24.2700","z":"24.6000","ts":"0"},{"tv":"-","s":"-","c":"","z":"-"}],"referer":"","userDelay":5000,"rtcode":"0000","queryTime":{"sysDate":"20260301","stockInfoItem":2484,"stockInfo":723,"sessionStr":"UserSession","sysTime":"14:59:58","showChart":false,"sessionFromTime":-1,"sessionLatestTime":-1},"rtmessage":"OK"}"""


class TestTWSEServiceE2E(unittest.TestCase):
    def test_parse_json_with_bom_and_jsonp_wrapper(self):
        wrapped = "\ufeffcallback(" + SAMPLE_TWSE_JSON + ");"
        data = _parse_twse_json(wrapped)
        self.assertIn("msgArray", data)
        self.assertEqual(data["msgArray"][0]["c"], "0050")
        self.assertEqual(data["msgArray"][2]["c"], "00919")

    @patch("app.services.twse_service.requests.get")
    def test_get_stock_quotes_end_to_end_from_raw_text(self, mock_get):
        mock_get.return_value = _FakeResponse("callback(" + SAMPLE_TWSE_JSON + ");")

        quotes = get_stock_quotes(["0050.TW", "00919"])

        self.assertEqual(set(quotes.keys()), {"0050", "00919"})
        self.assertEqual(quotes["0050"]["name"], "元大台灣50")
        self.assertEqual(quotes["0050"]["current_price"], Decimal("81.1500"))
        self.assertEqual(quotes["0050"]["yesterday_close"], Decimal("81.1000"))
        self.assertEqual(quotes["0050"]["time"], "13:30:00")

        self.assertEqual(quotes["00919"]["name"], "群益台灣精選高息")
        self.assertEqual(quotes["00919"]["current_price"], Decimal("24.6000"))
        self.assertEqual(quotes["00919"]["yesterday_close"], Decimal("24.2700"))

        requested_url = mock_get.call_args.kwargs.get("url") or mock_get.call_args.args[0]
        self.assertIn("tse_0050.tw", requested_url)
        self.assertIn("otc_0050.tw", requested_url)
        self.assertIn("tse_00919.tw", requested_url)
        self.assertIn("otc_00919.tw", requested_url)

    @patch("app.services.twse_service.requests.get")
    def test_fetch_twse_response_retry_without_verify_when_ssl_error(self, mock_get):
        mock_get.side_effect = [
            requests.exceptions.SSLError("cert verify failed"),
            _FakeResponse(SAMPLE_TWSE_JSON),
        ]

        response = _fetch_twse_response("https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_0050.tw")

        self.assertIsInstance(response, _FakeResponse)
        self.assertEqual(mock_get.call_count, 2)
        self.assertTrue(mock_get.call_args_list[0].kwargs["verify"])
        self.assertFalse(mock_get.call_args_list[1].kwargs["verify"])


if __name__ == "__main__":
    unittest.main()
