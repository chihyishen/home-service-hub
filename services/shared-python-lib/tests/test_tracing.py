import os

from fastapi import FastAPI
from shared_lib import tracing
from shared_lib.tracing import setup_tracing


def test_setup_tracing_no_live_exporter_under_pytest():
    # Guard: even strict=True with the endpoint present must NOT attach a live
    # OTLP exporter while pytest is loaded -- its daemon export thread races a
    # closed stderr at shutdown -> SIGABRT (exit 134). The provider is still
    # built (so the per-request trace_id works), it just has no span processors.
    os.environ["OTEL_COLLECTOR_ENDPOINT_GRPC"] = "http://localhost:4317"
    provider = setup_tracing("OTEL_SERVICE_NAME_X", "svc", strict=True)
    assert provider is not None
    # ponytail: peek the internal processor list -- the point is that nothing is
    # exporting, and OTel exposes no public getter for that.
    assert provider._active_span_processor._span_processors == ()


def test_fastapi_tracing_excludes_health_and_asgi_transport_spans(monkeypatch):
    os.environ["OTEL_COLLECTOR_ENDPOINT_GRPC"] = "http://localhost:4317"
    captured = {}

    def capture_instrumentation(app, **kwargs):
        captured["app"] = app
        captured.update(kwargs)

    monkeypatch.setattr(tracing.FastAPIInstrumentor, "instrument_app", capture_instrumentation)

    app = FastAPI()
    setup_tracing("OTEL_SERVICE_NAME_X", "svc", strict=True, app=app)

    assert captured["app"] is app
    assert captured["excluded_urls"] == r".*/health$"
    assert captured["exclude_spans"] == ["send", "receive"]
