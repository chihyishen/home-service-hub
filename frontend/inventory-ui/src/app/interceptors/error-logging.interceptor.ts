import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { trace, context } from '@opentelemetry/api';

export const errorLoggingInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      // 獲取當前 OpenTelemetry 的 Context 與 Span
      const activeSpan = trace.getSpan(context.active());
      const traceId = activeSpan?.spanContext().traceId;

      console.group('%c API Error Identified ', 'color: white; background: #eb4034; font-weight: bold;');
      console.error(`URL: ${req.url}`);
      console.error(`Status: ${error.status} (${error.statusText})`);
      if (traceId) {
        console.warn(`TraceID: ${traceId}`);
        console.log(`%c👉 Search this TraceID in Grafana Tempo to see the full backend flow.`, 'color: #3498db; font-style: italic;');
      } else {
        console.warn('TraceID: Not available (check if OTel is initialized)');
      }
      console.groupEnd();

      return throwError(() => error);
    })
  );
};
