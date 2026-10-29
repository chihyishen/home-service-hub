import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError, retry, of } from 'rxjs';
import { trace, context } from '@opentelemetry/api';
import { MessageService } from 'primeng/api';

export const errorLoggingInterceptor: HttpInterceptorFn = (req, next) => {
  const messageService = inject(MessageService);
  const request$ = next(req);
  const retryableRequest$ = req.method === 'GET' || req.method === 'HEAD'
    ? request$.pipe(retry({
        count: 1,
        delay: (error: HttpErrorResponse) => error.status >= 400 && error.status < 500
          ? throwError(() => error)
          : of(null)
      }))
    : request$;

  return retryableRequest$.pipe(
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
      
      const messages: Record<number, string> = {
        400: '請檢查輸入內容後再試。',
        401: '登入狀態已失效，請重新登入。',
        403: '您沒有權限執行此操作。',
        404: '找不到要求的資料。',
        422: '送出的資料格式不正確，請檢查後再試。',
        429: '操作過於頻繁，請稍後再試。'
      };
      const body = typeof error.error === 'object' && error.error !== null ? error.error : {};
      let errorMsg = error.status === 0
        ? '無法連線至伺服器，請檢查您的網路狀態。'
        : error.status >= 500
          ? '伺服器發生異常，請稍後再試。'
          : messages[error.status] || '要求失敗，請稍後再試。';
      const structuredMessage = typeof body.message === 'string' && body.message.trim()
        ? body.message
        : typeof body.detail === 'string' && body.detail.trim()
          ? body.detail
          : undefined;
      if (error.status >= 400 && error.status < 500 && structuredMessage) {
        errorMsg = structuredMessage;
      } else if (error.status === 422 && Array.isArray(body.detail)) {
        const details = body.detail
          .filter((item: { msg?: unknown }) => typeof item?.msg === 'string' && item.msg.trim())
          .map((item: { msg: string }) => item.msg);
        if (details.length) errorMsg = details.join('；');
      } else if (
        error.status >= 500
        && body.message === '內部伺服器錯誤，請稍後再試。'
      ) {
        errorMsg = body.message;
      }
      const correlationId = (error.status === 401 || error.status === 403 || error.status === 429)
        && typeof body.correlationId === 'string'
        && /^[A-Za-z0-9-]+$/.test(body.correlationId)
        ? body.correlationId
        : undefined;
      if (correlationId) errorMsg += `（參考編號：${correlationId}）`;
      
      messageService.add({ key: 'api-error', severity: 'error', summary: `錯誤 (${error.status})`, detail: errorMsg, life: 5000 });

      return throwError(() => error);
    })
  );
};
