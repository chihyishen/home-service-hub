import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { MessageService } from 'primeng/api';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { errorLoggingInterceptor } from './error-logging.interceptor';

describe('errorLoggingInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([errorLoggingInterceptor])),
        provideHttpClientTesting(),
        { provide: MessageService, useValue: { add: vi.fn() } }
      ]
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('retries a failed GET once', () => {
    http.get('/api/items').subscribe({ error: () => undefined });

    httpMock.expectOne('/api/items').flush({}, { status: 500, statusText: 'Server Error' });
    httpMock.expectOne('/api/items').flush({}, { status: 500, statusText: 'Server Error' });
    httpMock.verify();
  });

  it('does not retry a failed GET with a client error', () => {
    http.get('/api/items').subscribe({ error: () => undefined });

    httpMock.expectOne('/api/items').flush({}, { status: 404, statusText: 'Not Found' });
    httpMock.expectNone('/api/items');
    httpMock.verify();
  });

  it('does not retry a failed mutation', () => {
    http.post('/api/items/1/transactions', {}).subscribe({ error: () => undefined });

    httpMock.expectOne('/api/items/1/transactions').flush({}, { status: 500, statusText: 'Server Error' });
    httpMock.expectNone('/api/items/1/transactions');
    httpMock.verify();
  });

  it.each([
    [404, { message: '訂閱不存在' }, '訂閱不存在'],
    [400, { detail: '無效的訂閱項目' }, '無效的訂閱項目'],
    [409, { detail: '重新計算進行中' }, '重新計算進行中'],
    [401, { error: 'unauthorized', correlationId: 'req-401' }, '登入狀態已失效，請重新登入。（參考編號：req-401）'],
    [403, { error: 'forbidden', correlationId: 'req-403' }, '您沒有權限執行此操作。（參考編號：req-403）'],
    [403, { message: '需要管理員權限', correlationId: 'req-403' }, '需要管理員權限（參考編號：req-403）'],
    [429, { error: 'rate_limited', correlationId: 'req-429' }, '操作過於頻繁，請稍後再試。（參考編號：req-429）'],
    [500, { message: '內部伺服器錯誤，請稍後再試。' }, '內部伺服器錯誤，請稍後再試。'],
    [500, '<html>Internal Server Error</html>', '伺服器發生異常，請稍後再試。'],
    [422, { detail: [{ msg: '金額必須大於零' }] }, '金額必須大於零'],
    [0, {}, '無法連線至伺服器，請檢查您的網路狀態。'],
  ])('shows a safe localized error message for status %s', (status, body, detail) => {
    http.delete('/api/accounting/recurring/subscriptions/18').subscribe({ error: () => undefined });

    httpMock.expectOne('/api/accounting/recurring/subscriptions/18').flush(body, { status, statusText: 'Error' });

    expect(TestBed.inject(MessageService).add).toHaveBeenCalledWith(expect.objectContaining({
      key: 'api-error', severity: 'error', summary: `錯誤 (${status})`, detail,
    }));
    httpMock.verify();
  });
});
