import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpClient, HttpParams } from '@angular/common/http';
import { ShoppingListItemRequest, ShoppingListItemResponse } from '../models/item.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ShoppingListService {
  private http = inject(HttpClient);
  private baseUrl = `${environment.apiUrl}/shopping-list`;

  getList(status?: 'PENDING' | 'PURCHASED' | 'SKIPPED'): Observable<ShoppingListItemResponse[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    return this.http.get<ShoppingListItemResponse[]>(this.baseUrl, { params });
  }

  generateFromLowStock(): Observable<ShoppingListItemResponse[]> {
    return this.http.post<ShoppingListItemResponse[]>(`${this.baseUrl}/generate-from-low-stock`, {});
  }

  create(payload: Partial<ShoppingListItemResponse> | ShoppingListItemRequest): Observable<ShoppingListItemResponse> {
    return this.http.post<ShoppingListItemResponse>(this.baseUrl, payload);
  }

  update(id: number, payload: Partial<ShoppingListItemResponse> | ShoppingListItemRequest): Observable<ShoppingListItemResponse> {
    return this.http.patch<ShoppingListItemResponse>(`${this.baseUrl}/${id}`, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }
}
