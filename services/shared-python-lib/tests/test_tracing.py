import os

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
