import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ItemService } from '../../services/item.service';
import { ItemResponse } from '../../models/item.model';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-item-list',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="row mb-4 align-items-center">
      <div class="col-12 col-md">
        <h2 class="mb-2 mb-md-0">庫存物品</h2>
      </div>
      <div class="col-12 col-md-auto">
        <button routerLink="/add" class="btn btn-primary w-100 d-flex align-items-center justify-content-center">
          <i class="bi bi-plus-lg me-2"></i> 新增物品
        </button>
      </div>
    </div>

    <!-- 桌面版表格 (md 以上顯示) -->
    <div class="card d-none d-md-block">
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-hover mb-0" *ngIf="items().length > 0; else noItems">
            <thead class="table-light">
              <tr>
                <th class="ps-4">名稱</th>
                <th>類別</th>
                <th>位置</th>
                <th>數量</th>
                <th class="text-end pe-4">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let item of items()">
                <td class="ps-4 align-middle fw-medium">{{ item.name }}</td>
                <td class="align-middle">
                  <span class="badge bg-light text-dark border">{{ item.category }}</span>
                </td>
                <td class="align-middle text-muted">{{ item.location }}</td>
                <td class="align-middle">
                  <span class="badge" [ngClass]="item.quantity > 0 ? 'bg-success-subtle text-success border border-success' : 'bg-danger-subtle text-danger border border-danger'">
                    {{ item.quantity }}
                  </span>
                </td>
                <td class="text-end pe-4 align-middle">
                  <button [routerLink]="['/edit', item.id]" class="btn btn-outline-warning btn-sm me-2" title="編輯">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button (click)="deleteItem(item.id)" class="btn btn-outline-danger btn-sm" title="刪除">
                    <i class="bi bi-trash"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 手機版卡片 (md 以下顯示) -->
    <div class="d-md-none" *ngIf="items().length > 0; else noItems">
      <div class="card mb-3" *ngFor="let item of items()">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start mb-2">
            <h5 class="card-title mb-0 fw-bold">{{ item.name }}</h5>
            <span class="badge" [ngClass]="item.quantity > 0 ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'">
              數量: {{ item.quantity }}
            </span>
          </div>
          <div class="mb-3">
            <span class="badge bg-light text-dark border me-2">{{ item.category }}</span>
            <small class="text-muted"><i class="bi bi-geo-alt me-1"></i>{{ item.location }}</small>
          </div>
          <div class="d-flex gap-2">
            <button [routerLink]="['/edit', item.id]" class="btn btn-outline-warning flex-grow-1 btn-sm">
              <i class="bi bi-pencil me-1"></i> 編輯
            </button>
            <button (click)="deleteItem(item.id)" class="btn btn-outline-danger flex-grow-1 btn-sm">
              <i class="bi bi-trash me-1"></i> 刪除
            </button>
          </div>
        </div>
      </div>
    </div>

    <ng-template #noItems>
      <div class="card">
        <div class="card-body">
          <div class="text-center py-5">
            <i class="bi bi-box2-heart text-muted display-1"></i>
            <p class="mt-3 text-muted">目前沒有任何物品。</p>
            <button routerLink="/add" class="btn btn-outline-primary btn-sm mt-2">新增第一件物品</button>
          </div>
        </div>
      </div>
    </ng-template>
  `,
  styles: [`
    .table > :not(caption) > * > * { padding: 1rem 0.5rem; }
    .badge { font-weight: 500; font-size: 0.85rem; }
  `]
})
export class ItemListComponent implements OnInit {
  private itemService = inject(ItemService);
  items = signal<ItemResponse[]>([]);

  ngOnInit(): void {
    this.loadItems();
  }

  loadItems(): void {
    this.itemService.getAll().subscribe(data => {
      this.items.set(data);
    });
  }

  deleteItem(id: number): void {
    if (confirm('確定要刪除此物品嗎？')) {
      this.itemService.delete(id).subscribe(() => {
        this.loadItems();
      });
    }
  }
}
