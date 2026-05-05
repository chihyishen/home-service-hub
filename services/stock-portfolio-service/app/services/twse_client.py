import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Any, Callable, Generic, Optional, TypeVar

import requests
from requests import Response
from requests.exceptions import RequestException, SSLError

from shared_lib import get_tracer

try:
    import truststore
except ImportError:  # pragma: no cover - exercised in runtime environments without the dependency
    truststore = None


logger = logging.getLogger(__name__)
tracer = get_tracer("stock-portfolio-service")

T = TypeVar("T")

_truststore_lock = Lock()
_default_client_lock = Lock()
_truststore_injected = False
_default_client: Optional["TWSEClient"] = None


class TLSMode(str, Enum):
    FALLBACK = "fallback"
    VERIFY = "verify"
    INSECURE = "insecure"


@dataclass(frozen=True)
class TWSERequestPolicy:
    tls_mode: TLSMode = TLSMode.FALLBACK
    timeout_sec: float = 10.0
    retry_max_attempts: int = 2
    backoff_factor: float = 0.5
    quote_cache_ttl_sec: float = 30.0
    exdividend_cache_ttl_sec: float = 900.0

    @classmethod
    def from_env(cls) -> "TWSERequestPolicy":
        return cls(
            tls_mode=get_tls_mode(),
            timeout_sec=_get_float_env("TWSE_REQUEST_TIMEOUT_SEC", 10.0, minimum=0.1),
            retry_max_attempts=int(_get_float_env("TWSE_RETRY_MAX_ATTEMPTS", 2, minimum=1)),
            backoff_factor=_get_float_env("TWSE_RETRY_BACKOFF_FACTOR", 0.5, minimum=0.0),
            quote_cache_ttl_sec=_get_float_env("TWSE_QUOTE_CACHE_TTL_SEC", 30.0, minimum=0.0),
            exdividend_cache_ttl_sec=_get_float_env(
                "TWSE_EXDIVIDEND_CACHE_TTL_SEC", 900.0, minimum=0.0
            ),
        )


@dataclass(frozen=True)
class _CacheEntry(Generic[T]):
    expires_at: float
    value: T


class _TTLCache(Generic[T]):
    def __init__(self) -> None:
        self._entries: dict[Any, _CacheEntry[T]] = {}
        self._lock = Lock()

    def get(self, key: Any) -> Optional[T]:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                return None
            return entry.value

    def set(self, key: Any, value: T, ttl_sec: float) -> None:
        if ttl_sec <= 0:
            return
        with self._lock:
            self._entries[key] = _CacheEntry(expires_at=time.monotonic() + ttl_sec, value=value)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_quote_cache: _TTLCache[str] = _TTLCache()
_exdividend_cache: _TTLCache[list] = _TTLCache()


def _get_float_env(name: str, default: float, minimum: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError:
        logger.warning("Invalid %s=%s; using default %s", name, value, default)
        return default
    if parsed < minimum:
        logger.warning("%s below minimum %s; using default %s", name, minimum, default)
        return default
    return parsed


def bootstrap_truststore() -> None:
    """Inject the OS trust store into Python's ``ssl`` module exactly once.

    Process-global side effect: every HTTPS client in this process
    (TWSE, OTLP exporter, psycopg2, etc.) starts using the OS trust
    store after the first call. Safe to call repeatedly.
    """
    global _truststore_injected

    with _truststore_lock:
        if _truststore_injected:
            return

        if truststore is None:
            logger.warning("truststore is unavailable; continuing without OS trust store injection")
            _truststore_injected = True
            return

        try:
            truststore.inject_into_ssl()
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            logger.warning("truststore injection failed: %s", exc)
        finally:
            _truststore_injected = True


def get_tls_mode() -> TLSMode:
    raw_mode = (os.getenv("TWSE_TLS_MODE") or "").strip().lower()
    if raw_mode:
        if raw_mode == TLSMode.VERIFY.value:
            return TLSMode.VERIFY
        if raw_mode == TLSMode.INSECURE.value:
            logger.warning("TWSE_TLS_MODE=insecure is active; this is emergency-only mode")
            return TLSMode.INSECURE
        if raw_mode != TLSMode.FALLBACK.value:
            logger.warning("Unknown TWSE_TLS_MODE=%s; defaulting to fallback", raw_mode)
        return TLSMode.FALLBACK

    legacy_verify = os.getenv("TWSE_SSL_VERIFY")
    if legacy_verify is not None:
        normalized = legacy_verify.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            logger.warning("TWSE_SSL_VERIFY is deprecated; use TWSE_TLS_MODE=verify")
            return TLSMode.VERIFY
        if normalized in {"0", "false", "no", "off"}:
            logger.warning("TWSE_SSL_VERIFY is deprecated; use TWSE_TLS_MODE=fallback")
            return TLSMode.FALLBACK
        logger.warning("Unknown TWSE_SSL_VERIFY=%s; defaulting to fallback", legacy_verify)

    return TLSMode.FALLBACK


def get_twse_client() -> "TWSEClient":
    global _default_client

    with _default_client_lock:
        if _default_client is None:
            _default_client = TWSEClient(TWSERequestPolicy.from_env())
        return _default_client


def reset_twse_client_state() -> None:
    global _default_client, _truststore_injected

    with _default_client_lock:
        _default_client = None
    with _truststore_lock:
        _truststore_injected = False
    _quote_cache.clear()
    _exdividend_cache.clear()


class TWSEClient:
    def __init__(self, policy: TWSERequestPolicy) -> None:
        self.policy = policy

    def fetch_quote_text(self, url: str, symbols: list[str]) -> str:
        normalized_symbols = frozenset(_normalize_symbol(symbol) for symbol in symbols if _normalize_symbol(symbol))
        if not normalized_symbols:
            return ""

        return self._fetch(
            url=url,
            span_name="twse_quote_request",
            parser=lambda response: response.text,
            empty_value="",
            cache=_quote_cache,
            cache_key=normalized_symbols,
            cache_ttl_sec=self.policy.quote_cache_ttl_sec,
        )

    def fetch_exdividend_json(self, url: str) -> list:
        result = self._fetch(
            url=url,
            span_name="twse_exdividend_request",
            parser=lambda response: response.json(),
            empty_value=[],
            cache=_exdividend_cache,
            cache_key=url,
            cache_ttl_sec=self.policy.exdividend_cache_ttl_sec,
        )
        return result if isinstance(result, list) else []

    def _fetch(
        self,
        *,
        url: str,
        span_name: str,
        parser: Callable[[Response], T],
        empty_value: T,
        cache: _TTLCache[T],
        cache_key: Any,
        cache_ttl_sec: float,
    ) -> T:
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("http.url", url)

            cached_value = cache.get(cache_key)
            if cached_value is not None:
                span.set_attribute("cache.hit", True)
                return cached_value

            span.set_attribute("cache.hit", False)
            response = self._request(url, span)
            if response is None:
                return empty_value

            try:
                parsed = parser(response)
            except Exception as exc:
                logger.error("TWSE response parsing failed: %s", exc)
                return empty_value

            cache.set(cache_key, parsed, cache_ttl_sec)
            return parsed

    def _request(self, url: str, span: Any) -> Optional[Response]:
        bootstrap_truststore()

        if self.policy.tls_mode == TLSMode.INSECURE:
            logger.warning("TWSE insecure TLS mode is active")
            span.set_attribute("tls.verified", False)
            span.set_attribute("tls.fallback", False)
            return self._request_with_retries(url, verify=False, span=span)

        span.set_attribute("tls.verified", True)
        span.set_attribute("tls.fallback", False)
        try:
            return self._request_with_retries(url, verify=True, span=span)
        except SSLError as exc:
            if self.policy.tls_mode != TLSMode.FALLBACK:
                logger.error("TWSE verified request failed: %s", exc)
                return None

            logger.warning("TWSE TLS verification failed; retrying insecurely: %s", exc)
            span.set_attribute("tls.verified", False)
            span.set_attribute("tls.fallback", True)
            return self._request_once(url, verify=False, span=span)

    def _request_with_retries(self, url: str, *, verify: bool, span: Any) -> Optional[Response]:
        for attempt in range(1, self.policy.retry_max_attempts + 1):
            try:
                return self._request_once(url, verify=verify, span=span, log_errors=False)
            except SSLError:
                raise
            except RequestException as exc:
                if attempt >= self.policy.retry_max_attempts:
                    logger.error("TWSE request failed after %s attempts: %s", attempt, exc)
                    return None

                delay = self.policy.backoff_factor * (2 ** (attempt - 1))
                logger.warning(
                    "TWSE request attempt %s/%s failed, retrying in %.2fs: %s",
                    attempt,
                    self.policy.retry_max_attempts,
                    delay,
                    exc,
                )
                if delay > 0:
                    time.sleep(delay)

        return None

    def _request_once(
        self,
        url: str,
        *,
        verify: bool,
        span: Any,
        log_errors: bool = True,
    ) -> Optional[Response]:
        try:
            response = requests.get(url, timeout=self.policy.timeout_sec, verify=verify)
            span.set_attribute("http.status", response.status_code)
            response.raise_for_status()
            return response
        except SSLError:
            raise
        except RequestException as exc:
            if log_errors:
                logger.error("TWSE request failed: %s", exc)
                return None
            raise exc


def _normalize_symbol(symbol: str) -> str:
    return symbol.split(".")[0].upper().strip()
