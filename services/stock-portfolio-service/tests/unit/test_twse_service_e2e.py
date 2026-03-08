import unittest
from decimal import Decimal
from unittest.mock import patch

from app.services.twse_service import fetch_raw_quotes, get_stock_quotes, parse_twse_msg_array


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


SAMPLE_TWSE_JSON = """{"msgArray":[{"c":"0050","n":"元大台灣50","z":"81.1500","y":"81.1000","t":"13:30:00"},{"c":"00919","n":"群益台灣精選高息","z":"24.6000","y":"24.2700","t":"13:30:00"}],"rtcode":"0000"}"""


class TestTWSEServiceE2E(unittest.TestCase):
    @patch("app.services.twse_service.requests.get")
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

    @patch("app.services.twse_service.requests.get")
    def test_get_stock_quotes(self, mock_get):
        mock_get.return_value = _FakeResponse("callback(" + SAMPLE_TWSE_JSON + ");")
        quotes = get_stock_quotes(["0050.TW", "00919"])
        self.assertEqual(set(quotes.keys()), {"0050", "00919"})
        requested_url = mock_get.call_args.kwargs.get("url") or mock_get.call_args.args[0]
        self.assertIn("tse_0050.tw", requested_url)
        self.assertIn("tse_00919.tw", requested_url)


if __name__ == "__main__":
    unittest.main()
