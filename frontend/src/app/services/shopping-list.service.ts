import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpParams } from '@angular/common/http';
import { BaseApiService } from './base-api.service';
import { ShoppingListItemRequest, ShoppingListItemResponse } from '../models/item.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ShoppingListService extends BaseApiService<ShoppingListItemResponse> {
  protected override baseUrl = `${environment.apiUrl}/shopping-list`;

  getList(status?: 'PENDING' | 'PURCHASED' | 'SKIPPED'): Observable<ShoppingListItemResponse[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    return this.getAll(params);
  }

  generateFromLowStock(): Observable<ShoppingListItemResponse[]> {
    return this.http.post<ShoppingListItemResponse[]>(`${this.baseUrl}/generate-from-low-stock`, {});
  }

  override create(payload: Partial<ShoppingListItemResponse> | ShoppingListItemRequest): Observable<ShoppingListItemResponse> {
    return this.http.post<ShoppingListItemResponse>(this.baseUrl, payload);
  }

  override update(id: number, payload: Partial<ShoppingListItemResponse> | ShoppingListItemRequest): Observable<ShoppingListItemResponse> {
    return this.http.patch<ShoppingListItemResponse>(`${this.baseUrl}/${id}`, payload);
  }

  delete(id: number): Observable<void> {
    return this.remove(id);
  }
}
