"""Mocked TWSE unit tests that stay in the default test run."""

import unittest
from decimal import Decimal
from unittest.mock import patch

from app.services.twse_client import reset_twse_client_state
from app.services.twse_service import fetch_raw_quotes, get_stock_quotes, parse_twse_msg_array


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text
        self.status_code = 200

    def raise_for_status(self):
        return None


SAMPLE_TWSE_JSON = """{"msgArray":[{"c":"0050","n":"元大台灣50","z":"81.1500","y":"81.1000","t":"13:30:00"},{"c":"00919","n":"群益台灣精選高息","z":"24.6000","y":"24.2700","t":"13:30:00"}],"rtcode":"0000"}"""


class TestTWSEServiceMocked(unittest.TestCase):
    def setUp(self):
        reset_twse_client_state()

    @patch("app.services.twse_client.requests.get")
    def test_fetch_raw_quotes_from_text(self, mock_get):
        mock_get.return_value = _FakeResponse("\ufeffcallback(" + SAMPLE_TWSE_JSON + ");")
        data = fetch_raw_quotes(["0050.TW", "00919"])
        self.assertIn("msgArray", data)
        self.assertEqual(data["msgArray"][0]["c"], "0050")

    def test_parse_twse_msg_array(self):
        msg_array = [
            {"c": "0050", "n": "元大台灣50", "z": "81.1500", "y": "81.1000", "t": "13:30:00"},
            {"c": "00919", "n": "群益台灣精選高息", "z": "24.6000", "y": "24.2700", "t": "13:30:00"},
        ]
        parsed = parse_twse_msg_array(msg_array, ["0050", "00919"])
        self.assertEqual(set(parsed.keys()), {"0050", "00919"})
        self.assertEqual(parsed["0050"]["current_price"], Decimal("81.1500"))
        self.assertEqual(parsed["00919"]["yesterday_close"], Decimal("24.2700"))

    def test_parse_locked_limit_up_uses_limit_price(self):
        # 2026-11-24 0050 live payload: no trade, no ask, bids stacked at limit-up
        msg_array = [
            {"c": "0050", "z": "-", "pz": "-", "a": "-", "y": "87.0000", "u": "95.7000",
             "b": "0.0000_95.7000_95.6500_95.6000_95.5500_"},
            {"c": "00919", "z": "-", "pz": "-", "y": "27.1200", "u": "29.8300",
             "a": "29.7500_29.7600_", "b": "29.7400_29.7300_"},
        ]
        parsed = parse_twse_msg_array(msg_array, ["0050", "00919"])
        self.assertEqual(parsed["0050"]["current_price"], Decimal("95.7000"))
        self.assertEqual(parsed["00919"]["current_price"], Decimal("29.7500"))  # not locked: unchanged path

    def test_parse_locked_limit_down_uses_limit_price(self):
        # mirror of limit-up: no trade, no bid, asks stacked at limit-down (first ask 0.0000 = market sell)
        msg_array = [
            {"c": "0050", "z": "-", "pz": "-", "b": "-", "y": "87.0000", "u": "95.7000", "w": "78.3000",
             "a": "0.0000_78.3000_78.3500_78.4000_78.4500_"},
        ]
        parsed = parse_twse_msg_array(msg_array, ["0050"])
        self.assertEqual(parsed["0050"]["current_price"], Decimal("78.3000"))

    @patch("app.services.twse_client.requests.get")
    def test_get_stock_quotes(self, mock_get):
        mock_get.return_value = _FakeResponse("callback(" + SAMPLE_TWSE_JSON + ");")
        quotes = get_stock_quotes(["0050.TW", "00919"])
        self.assertEqual(set(quotes.keys()), {"0050", "00919"})
        requested_url = mock_get.call_args.kwargs.get("url") or mock_get.call_args.args[0]
        self.assertIn("tse_0050.tw", requested_url)
        self.assertIn("tse_00919.tw", requested_url)


if __name__ == "__main__":
    unittest.main()
