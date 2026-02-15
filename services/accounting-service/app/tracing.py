import os
import logging
from opentelemetry import trace, _logs
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

def setup_tracing(app=None, engine=None):
    # 嚴格讀取環境變數
    service_name = os.getenv("OTEL_SERVICE_NAME_ACCOUNTING")
    otlp_endpoint = os.getenv("OTEL_COLLECTOR_ENDPOINT_GRPC")

    if not service_name or not otlp_endpoint:
        missing = [k for k, v in {"OTEL_SERVICE_NAME_ACCOUNTING": service_name, "OTEL_COLLECTOR_ENDPOINT_GRPC": otlp_endpoint}.items() if not v]
        raise ValueError(f"❌ 缺少必要的 OpenTelemetry 環境變數: {', '.join(missing)}")

    resource = Resource.create({"service.name": service_name})

    # --- 1. Tracing ---
    trace_provider = TracerProvider(resource=resource)
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)

    # --- 2. Logging ---
    logger_provider = LoggerProvider(resource=resource)
    _logs.set_logger_provider(logger_provider)
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    log_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    # 掛載 Handler
    otel_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(otel_handler)
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        logging.getLogger(logger_name).addHandler(otel_handler)

    # 3. 自動儀表化
    LoggingInstrumentor().instrument(set_logging_format=True)
    if app:
        FastAPIInstrumentor.instrument_app(app)
    if engine:
        SQLAlchemyInstrumentor().instrument(engine=engine)

    return trace_provider

tracer = trace.get_tracer("accounting-service")
