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

  it('does not retry a failed mutation', () => {
    http.post('/api/items/1/transactions', {}).subscribe({ error: () => undefined });

    httpMock.expectOne('/api/items/1/transactions').flush({}, { status: 500, statusText: 'Server Error' });
    httpMock.expectNone('/api/items/1/transactions');
    httpMock.verify();
  });
});
