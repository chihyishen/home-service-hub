from __future__ import annotations

import logging
import os
import sys

from opentelemetry import _logs, trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_logging_instrumented = False
_requests_instrumented = False


def _normalize_endpoint(endpoint: str) -> str:
    return endpoint.replace("http://", "").replace("https://", "")


def _attach_handler(logger: logging.Logger, handler: LoggingHandler) -> None:
    if not any(isinstance(existing_handler, LoggingHandler) for existing_handler in logger.handlers):
        logger.addHandler(handler)


def setup_tracing(service_name_env: str, default_service_name: str | None = None, strict: bool = True, app=None, engine=None):
    # ponytail: under pytest we still build the provider and instrument the app
    # (the error handler stamps each response with the request's trace_id, which
    # tests assert on), but we skip the live OTLP exporters. Their daemon export
    # thread retries a (usually dead) collector and can race a closed stderr at
    # interpreter shutdown -> SIGABRT/exit 134, even with every test green.
    under_pytest = "pytest" in sys.modules

    service_name = os.getenv(service_name_env, default_service_name)
    otlp_endpoint = os.getenv("OTEL_COLLECTOR_ENDPOINT_GRPC")

    missing_vars = []
    if not service_name:
        missing_vars.append(service_name_env)
    if not otlp_endpoint and not under_pytest:
        missing_vars.append("OTEL_COLLECTOR_ENDPOINT_GRPC")

    if missing_vars:
        if strict:
            raise ValueError(
                f"Missing required OpenTelemetry environment variables: {', '.join(missing_vars)}"
            )
        logging.warning(
            "OpenTelemetry disabled because required environment variables are missing: %s",
            ", ".join(missing_vars),
        )
        return None

    logging.getLogger().setLevel(logging.INFO)

    resource = Resource.create({"service.name": service_name})
    trace_provider = TracerProvider(resource=resource)

    if not under_pytest:
        clean_endpoint = _normalize_endpoint(otlp_endpoint)
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        trace_exporter = OTLPSpanExporter(endpoint=clean_endpoint, insecure=True)
        trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))

    trace.set_tracer_provider(trace_provider)

    if not under_pytest:
        logger_provider = LoggerProvider(resource=resource)
        _logs.set_logger_provider(logger_provider)
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

        log_exporter = OTLPLogExporter(endpoint=clean_endpoint, insecure=True)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

        otel_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
        _attach_handler(logging.getLogger(), otel_handler)
        for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)
            _attach_handler(logger, otel_handler)

    global _logging_instrumented, _requests_instrumented
    if not _logging_instrumented:
        LoggingInstrumentor().instrument(set_logging_format=True)
        _logging_instrumented = True
    if not _requests_instrumented:
        RequestsInstrumentor().instrument()
        _requests_instrumented = True

    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
    if engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine)

    return trace_provider


def get_tracer(name: str):
    return trace.get_tracer(name)
