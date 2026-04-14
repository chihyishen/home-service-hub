from shared_lib.tracing import setup_tracing as _setup_tracing, get_tracer


def setup_tracing(app=None, engine=None):
    return _setup_tracing(
        service_name_env="OTEL_SERVICE_NAME_STOCK",
        default_service_name="stock-portfolio-service",
        strict=False,
        app=app,
        engine=engine,
    )


tracer = get_tracer("stock-portfolio-service")
