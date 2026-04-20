import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';
import { BaseApiService } from './base-api.service';
import {
  ItemRequest,
  ItemResponse,
  InventoryTransactionRequest,
  InventoryTransactionResponse,
  ItemTransactionResultResponse
} from '../models/item.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ItemService extends BaseApiService<ItemResponse> {
  protected override baseUrl = `${environment.apiUrl}/items`;

  getAllFiltered(keyword?: string, lowStockOnly?: boolean, category?: string, location?: string): Observable<ItemResponse[]> {
    let params = new HttpParams();
    if (keyword) params = params.set('keyword', keyword);
    if (lowStockOnly) params = params.set('lowStockOnly', String(lowStockOnly));
    if (category) params = params.set('category', category);
    if (location) params = params.set('location', location);
    return this.http.get<ItemResponse[]>(this.baseUrl, { params });
  }

  getCategories(): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/categories`);
  }

  getLocations(): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/locations`);
  }

  getById(id: number): Observable<ItemResponse> {
    return this.getOne(id);
  }

  override create(item: Partial<ItemResponse> | ItemRequest): Observable<ItemResponse> {
    return this.http.post<ItemResponse>(this.baseUrl, item);
  }

  override update(id: number, item: Partial<ItemResponse> | ItemRequest): Observable<ItemResponse> {
    return this.http.put<ItemResponse>(`${this.baseUrl}/${id}`, item);
  }

  uploadImage(id: number, file: File): Observable<ItemResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ItemResponse>(`${this.baseUrl}/${id}/image`, formData);
  }

  delete(id: number): Observable<void> {
    return this.remove(id);
  }

  createTransaction(id: number, payload: InventoryTransactionRequest): Observable<ItemTransactionResultResponse> {
    return this.http.post<ItemTransactionResultResponse>(`${this.baseUrl}/${id}/transactions`, payload);
  }

  getTransactions(id: number, limit: number = 50): Observable<InventoryTransactionResponse[]> {
    return this.http.get<InventoryTransactionResponse[]>(`${this.baseUrl}/${id}/transactions`, { params: { limit } });
  }
}
