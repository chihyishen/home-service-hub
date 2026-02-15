import os
import logging
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# 引入日誌相關組件
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

def setup_tracing(app=None, engine=None):
    service_name = os.getenv("OTEL_SERVICE_NAME", "accounting-service")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    # 建立 Resource，確保 service.name 正確
    resource = Resource.create({"service.name": service_name})
    
    # --- 1. Trace 設定 ---
    provider = TracerProvider(resource=resource)
    if "4318" in otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    else:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)

    provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(provider)

    # --- 2. Log 設定 ---
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)
    
    if "4318" in otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    else:
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    
    log_exporter = OTLPLogExporter(endpoint=otlp_endpoint)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    # 建立 OTel Logging Handler
    otel_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)

    # 【重要】將 Handler 掛載到全域與 Uvicorn 相關的 Loggers
    # 這樣才能捕捉到框架本身的日誌
    loggers = [
        logging.getLogger(), # Root logger
        logging.getLogger("uvicorn"),
        logging.getLogger("uvicorn.error"),
        logging.getLogger("uvicorn.access"),
        logging.getLogger("fastapi")
    ]
    
    for logger in loggers:
        logger.addHandler(otel_handler)
        logger.setLevel(logging.INFO)

    # 讓 Trace ID 注入到 Console Log 格式中
    LoggingInstrumentor().instrument(set_logging_format=True)

    if app:
        FastAPIInstrumentor.instrument_app(app)
    if engine:
        SQLAlchemyInstrumentor().instrument(engine=engine)

    return provider

# 使用服務名稱作為 tracer 名稱
tracer = trace.get_tracer("accounting-service")
