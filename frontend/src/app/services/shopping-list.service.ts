import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { ShoppingListItemRequest, ShoppingListItemResponse } from '../models/item.model';

@Injectable({
  providedIn: 'root'
})
export class ShoppingListService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/shopping-list`;

  getList(status?: 'PENDING' | 'PURCHASED' | 'SKIPPED'): Observable<ShoppingListItemResponse[]> {
    const params: { [key: string]: string } = {};
    if (status) {
      params['status'] = status;
    }
    return this.http.get<ShoppingListItemResponse[]>(this.apiUrl, { params });
  }

  generateFromLowStock(): Observable<ShoppingListItemResponse[]> {
    return this.http.post<ShoppingListItemResponse[]>(`${this.apiUrl}/generate-from-low-stock`, {});
  }

  create(payload: ShoppingListItemRequest): Observable<ShoppingListItemResponse> {
    return this.http.post<ShoppingListItemResponse>(this.apiUrl, payload);
  }

  update(id: number, payload: ShoppingListItemRequest): Observable<ShoppingListItemResponse> {
    return this.http.patch<ShoppingListItemResponse>(`${this.apiUrl}/${id}`, payload);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
