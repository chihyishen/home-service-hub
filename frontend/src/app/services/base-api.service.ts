import { inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export abstract class BaseApiService<T extends { id?: number }> {
  protected http = inject(HttpClient);
  protected abstract baseUrl: string;

  getAll(params?: HttpParams): Observable<T[]> {
    return this.http.get<T[]>(this.baseUrl, { params });
  }

  getOne(id: number): Observable<T> {
    return this.http.get<T>(`${this.baseUrl}/${id}`);
  }

  create(body: Partial<T>): Observable<T> {
    return this.http.post<T>(this.baseUrl, body);
  }

  update(id: number, body: Partial<T>): Observable<T> {
    return this.http.put<T>(`${this.baseUrl}/${id}`, body);
  }

  remove(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }
}
