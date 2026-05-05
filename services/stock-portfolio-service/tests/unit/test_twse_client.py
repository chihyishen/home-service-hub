from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError, SSLError

from app.services import twse_client
from app.services.twse_client import (
    TLSMode,
    TWSEClient,
    TWSERequestPolicy,
    bootstrap_truststore,
    get_tls_mode,
    reset_twse_client_state,
)


class _FakeResponse:
    def __init__(self, text: str = "", json_data=None, status_code: int = 200):
        self.text = text
        self._json_data = [] if json_data is None else json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise ConnectionError(f"status={self.status_code}")

    def json(self):
        return self._json_data


@pytest.fixture(autouse=True)
def _reset_twse_state():
    reset_twse_client_state()
    yield
    reset_twse_client_state()


def _policy(tls_mode: TLSMode, *, quote_ttl: float = 30.0, exdiv_ttl: float = 900.0, retry_max_attempts: int = 2):
    return TWSERequestPolicy(
        tls_mode=tls_mode,
        timeout_sec=10.0,
        retry_max_attempts=retry_max_attempts,
        backoff_factor=0.5,
        quote_cache_ttl_sec=quote_ttl,
        exdividend_cache_ttl_sec=exdiv_ttl,
    )


def test_tls_mode_defaults_to_fallback(monkeypatch):
    monkeypatch.delenv("TWSE_TLS_MODE", raising=False)
    monkeypatch.delenv("TWSE_SSL_VERIFY", raising=False)

    assert get_tls_mode() == TLSMode.FALLBACK


def test_tls_mode_legacy_ssl_verify_true_maps_to_verify(monkeypatch, caplog):
    monkeypatch.delenv("TWSE_TLS_MODE", raising=False)
    monkeypatch.setenv("TWSE_SSL_VERIFY", "true")

    assert get_tls_mode() == TLSMode.VERIFY
    assert "deprecated" in caplog.text


@patch("app.services.twse_client.requests.get")
def test_fallback_mode_retries_with_verify_false_on_sslerror(mock_get):
    client = TWSEClient(_policy(TLSMode.FALLBACK))
    mock_get.side_effect = [SSLError("certificate verify failed"), _FakeResponse(json_data=[])]

    result = client.fetch_exdividend_json("https://example.test/exdiv")

    assert result == []
    assert mock_get.call_count == 2
    assert mock_get.call_args_list[0].kwargs["verify"] is True
    assert mock_get.call_args_list[1].kwargs["verify"] is False


@patch("app.services.twse_client.requests.get")
@patch("app.services.twse_client.tracer.start_as_current_span")
def test_fallback_mode_sets_observable_span_attributes(mock_start_span, mock_get):
    mock_span = MagicMock()
    mock_start_span.return_value.__enter__.return_value = mock_span
    client = TWSEClient(_policy(TLSMode.FALLBACK))
    mock_get.side_effect = [SSLError("certificate verify failed"), _FakeResponse(json_data=[])]

    client.fetch_exdividend_json("https://example.test/exdiv")

    attribute_map = {call.args[0]: call.args[1] for call in mock_span.set_attribute.call_args_list}
    assert attribute_map["cache.hit"] is False
    assert attribute_map["tls.fallback"] is True
    assert attribute_map["tls.verified"] is False
    assert attribute_map["http.status"] == 200


@patch("app.services.twse_client.requests.get")
@patch("app.services.twse_client.tracer.start_as_current_span")
def test_http_error_sets_status_span_attribute(mock_start_span, mock_get):
    mock_span = MagicMock()
    mock_start_span.return_value.__enter__.return_value = mock_span
    client = TWSEClient(_policy(TLSMode.FALLBACK, retry_max_attempts=1))
    mock_get.return_value = _FakeResponse(status_code=503)

    result = client.fetch_exdividend_json("https://example.test/exdiv")

    assert result == []
    attribute_map = {call.args[0]: call.args[1] for call in mock_span.set_attribute.call_args_list}
    assert attribute_map["http.status"] == 503


@patch("app.services.twse_client.requests.get")
def test_non_sslerror_does_not_trigger_insecure_fallback(mock_get):
    client = TWSEClient(_policy(TLSMode.FALLBACK, retry_max_attempts=1))
    mock_get.side_effect = ConnectionError("boom")

    result = client.fetch_exdividend_json("https://example.test/exdiv")

    assert result == []
    assert mock_get.call_count == 1
    assert mock_get.call_args.kwargs["verify"] is True


@patch("app.services.twse_client.requests.get")
def test_verify_mode_never_falls_back(mock_get):
    client = TWSEClient(_policy(TLSMode.VERIFY, retry_max_attempts=1))
    mock_get.side_effect = SSLError("certificate verify failed")

    result = client.fetch_exdividend_json("https://example.test/exdiv")

    assert result == []
    assert mock_get.call_count == 1
    assert mock_get.call_args.kwargs["verify"] is True


@patch("app.services.twse_client.requests.get")
def test_insecure_mode_uses_verify_false(mock_get, caplog):
    client = TWSEClient(_policy(TLSMode.INSECURE, retry_max_attempts=1))
    mock_get.return_value = _FakeResponse(json_data=[])

    result = client.fetch_exdividend_json("https://example.test/exdiv")

    assert result == []
    assert mock_get.call_args.kwargs["verify"] is False
    assert "insecure TLS mode" in caplog.text


@patch("app.services.twse_client.requests.get")
def test_quote_cache_hits_for_same_symbol_set_regardless_of_order(mock_get):
    client = TWSEClient(_policy(TLSMode.FALLBACK, quote_ttl=30.0))
    mock_get.return_value = _FakeResponse(text="callback({\"msgArray\":[]});")

    first = client.fetch_quote_text("https://example.test/quotes", ["0050", "2330"])
    second = client.fetch_quote_text("https://example.test/quotes", ["2330", "0050"])

    assert first == second
    assert mock_get.call_count == 1


@patch("app.services.twse_client.requests.get")
def test_quote_cache_expires(mock_get, monkeypatch):
    current_time = {"value": 0.0}
    monkeypatch.setattr(twse_client.time, "monotonic", lambda: current_time["value"])

    client = TWSEClient(_policy(TLSMode.FALLBACK, quote_ttl=30.0))
    mock_get.return_value = _FakeResponse(text="callback({\"msgArray\":[]});")

    client.fetch_quote_text("https://example.test/quotes", ["0050"])
    current_time["value"] = 31.0
    client.fetch_quote_text("https://example.test/quotes", ["0050"])

    assert mock_get.call_count == 2


@patch("app.services.twse_client.requests.get")
def test_exdividend_cache_hits(mock_get):
    client = TWSEClient(_policy(TLSMode.FALLBACK, exdiv_ttl=900.0))
    mock_get.return_value = _FakeResponse(json_data=[{"股票代號": "2330"}])

    first = client.fetch_exdividend_json("https://example.test/exdiv")
    second = client.fetch_exdividend_json("https://example.test/exdiv")

    assert first == second == [{"股票代號": "2330"}]
    assert mock_get.call_count == 1


def test_truststore_bootstrap_is_idempotent():
    with patch("app.services.twse_client.truststore") as mock_truststore:
        mock_truststore.inject_into_ssl = MagicMock()
        bootstrap_truststore()
        bootstrap_truststore()

    assert mock_truststore.inject_into_ssl.call_count == 1
