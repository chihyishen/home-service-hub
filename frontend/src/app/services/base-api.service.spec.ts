import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BaseApiService } from './base-api.service';

interface TestItem {
  id: number;
  name: string;
}

@Injectable({ providedIn: 'root' })
class TestService extends BaseApiService<TestItem> {
  protected override baseUrl = '/api/test';
}

describe('BaseApiService', () => {
  let service: TestService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), TestService]
    });
    service = TestBed.inject(TestService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('getAll sends GET to baseUrl', () => {
    service.getAll().subscribe(items => {
      expect(items).toEqual([{ id: 1, name: 'test' }]);
    });
    const req = httpMock.expectOne('/api/test');
    expect(req.request.method).toBe('GET');
    req.flush([{ id: 1, name: 'test' }]);
  });

  it('getOne sends GET to baseUrl/:id', () => {
    service.getOne(42).subscribe(item => {
      expect(item.name).toBe('hello');
    });
    const req = httpMock.expectOne('/api/test/42');
    expect(req.request.method).toBe('GET');
    req.flush({ id: 42, name: 'hello' });
  });

  it('create sends POST to baseUrl', () => {
    const payload = { name: 'new' };
    service.create(payload).subscribe();
    const req = httpMock.expectOne('/api/test');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(payload);
    req.flush({ id: 1, name: 'new' });
  });

  it('update sends PUT to baseUrl/:id', () => {
    service.update(1, { name: 'updated' }).subscribe();
    const req = httpMock.expectOne('/api/test/1');
    expect(req.request.method).toBe('PUT');
    req.flush({ id: 1, name: 'updated' });
  });

  it('remove sends DELETE to baseUrl/:id', () => {
    service.remove(1).subscribe();
    const req = httpMock.expectOne('/api/test/1');
    expect(req.request.method).toBe('DELETE');
    req.flush(null);
  });
});
