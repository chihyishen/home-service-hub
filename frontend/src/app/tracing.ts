import { WebTracerProvider, BatchSpanProcessor } from '@opentelemetry/sdk-trace-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { XMLHttpRequestInstrumentation } from '@opentelemetry/instrumentation-xml-http-request';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { resourceFromAttributes } from '@opentelemetry/resources';
import { ATTR_SERVICE_NAME } from '@opentelemetry/semantic-conventions';
import { environment } from '../environments/environment';

export function initTracing() {
  const exporter = new OTLPTraceExporter({
    url: `/otlp/v1/traces`,
  });

  // 在 OpenTelemetry JS 2.x 中，ESM 導出建議使用 resourceFromAttributes
  const resource = resourceFromAttributes({
    [ATTR_SERVICE_NAME]: 'inventory-ui',
  });

  const provider = new WebTracerProvider({
    resource: resource,
    spanProcessors: [new BatchSpanProcessor(exporter)]
  });

  provider.register({
    contextManager: new ZoneContextManager(),
  });

  registerInstrumentations({
    instrumentations: [
      new DocumentLoadInstrumentation(),
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: [
           new RegExp(`http://${environment.inventoryServiceHost}:${environment.inventoryServicePort}/.*`),
           new RegExp(`http://${environment.accountingServiceHost}:${environment.accountingServicePort}/.*`),
           new RegExp(`${window.location.origin}/api/.*`)
        ],
      }),
      new XMLHttpRequestInstrumentation({
        propagateTraceHeaderCorsUrls: [
           new RegExp(`http://${environment.inventoryServiceHost}:${environment.inventoryServicePort}/.*`),
           new RegExp(`http://${environment.accountingServiceHost}:${environment.accountingServicePort}/.*`),
           new RegExp(`${window.location.origin}/api/.*`)
        ],
      }),
    ],
  });

  console.log('OpenTelemetry Tracing initialized');
}
