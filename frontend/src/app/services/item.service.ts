import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {
  ItemRequest,
  ItemResponse,
  InventoryTransactionRequest,
  InventoryTransactionResponse,
  ItemTransactionResultResponse
} from '../models/item.model';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ItemService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/items`;

  getAll(keyword?: string, lowStockOnly?: boolean, category?: string, location?: string): Observable<ItemResponse[]> {
    const params: any = {};
    if (keyword) {
      params.keyword = keyword;
    }
    if (lowStockOnly) {
      params.lowStockOnly = lowStockOnly;
    }
    if (category) {
      params.category = category;
    }
    if (location) {
      params.location = location;
    }
    return this.http.get<ItemResponse[]>(this.apiUrl, { params });
  }

  getCategories(): Observable<string[]> {
    return this.http.get<string[]>(`${this.apiUrl}/categories`);
  }

  getLocations(): Observable<string[]> {
    return this.http.get<string[]>(`${this.apiUrl}/locations`);
  }

  getById(id: number): Observable<ItemResponse> {
    return this.http.get<ItemResponse>(`${this.apiUrl}/${id}`);
  }

  create(item: ItemRequest): Observable<ItemResponse> {
    return this.http.post<ItemResponse>(this.apiUrl, item);
  }

  update(id: number, item: ItemRequest): Observable<ItemResponse> {
    return this.http.put<ItemResponse>(`${this.apiUrl}/${id}`, item);
  }

  uploadImage(id: number, file: File): Observable<ItemResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ItemResponse>(`${this.apiUrl}/${id}/image`, formData);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  createTransaction(id: number, payload: InventoryTransactionRequest): Observable<ItemTransactionResultResponse> {
    return this.http.post<ItemTransactionResultResponse>(`${this.apiUrl}/${id}/transactions`, payload);
  }

  getTransactions(id: number, limit: number = 50): Observable<InventoryTransactionResponse[]> {
    return this.http.get<InventoryTransactionResponse[]>(`${this.apiUrl}/${id}/transactions`, { params: { limit } });
  }
}
