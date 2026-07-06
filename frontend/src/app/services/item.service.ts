import { Injectable } from '@angular/core';
import { Observable, defer } from 'rxjs';
import { switchMap } from 'rxjs/operators';
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
    return defer(() => this.normalizeImage(file)).pipe(
      switchMap(normalized => {
        const formData = new FormData();
        formData.append('file', normalized);
        return this.http.post<ItemResponse>(`${this.baseUrl}/${id}/image`, formData);
      })
    );
  }

  // ponytail: fixed knobs (1600px longest edge, 0.8 JPEG quality) — good enough for phone
  // photos, not worth making configurable. Falls back to the original file on any failure
  // (unsupported browser, non-image, canvas errors) so uploads are never blocked.
  private async normalizeImage(file: File): Promise<File> {
    if (!file.type.startsWith('image/')) {
      return file;
    }
    try {
      const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
      const maxEdge = 1600;
      const scale = Math.min(1, maxEdge / Math.max(bitmap.width, bitmap.height));
      const width = Math.round(bitmap.width * scale);
      const height = Math.round(bitmap.height * scale);

      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        return file;
      }
      ctx.drawImage(bitmap, 0, 0, width, height);

      const blob: Blob | null = await new Promise(resolve =>
        canvas.toBlob(resolve, 'image/jpeg', 0.8)
      );
      if (!blob) {
        return file;
      }

      const baseName = file.name.replace(/\.[^./\\]+$/, '') || 'photo';
      return new File([blob], `${baseName}.jpg`, { type: 'image/jpeg' });
    } catch {
      return file;
    }
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
