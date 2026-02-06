import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ItemRequest, ItemResponse } from '../models/item.model';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ItemService {
  private http = inject(HttpClient);
  private apiUrl = 'http://localhost:1031/api/items';

  getAll(): Observable<ItemResponse[]> {
    return this.http.get<ItemResponse[]>(this.apiUrl);
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

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }
}
