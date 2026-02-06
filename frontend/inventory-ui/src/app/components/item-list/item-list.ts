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
      <div class="col">
        <h2 class="mb-0">Inventory Items</h2>
      </div>
      <div class="col-auto">
        <button routerLink="/add" class="btn btn-primary d-flex align-items-center">
          <i class="bi bi-plus-lg me-2"></i> Add New Item
        </button>
      </div>
    </div>

    <div class="card">
      <div class="card-body p-0">
        <div class="table-responsive">
          <table class="table table-hover mb-0" *ngIf="items().length > 0; else noItems">
            <thead class="table-light">
              <tr>
                <th class="ps-4">Name</th>
                <th>Category</th>
                <th>Location</th>
                <th>Quantity</th>
                <th class="text-end pe-4">Actions</th>
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
                  <button [routerLink]="['/edit', item.id]" class="btn btn-outline-warning btn-sm me-2" title="Edit">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button (click)="deleteItem(item.id)" class="btn btn-outline-danger btn-sm" title="Delete">
                    <i class="bi bi-trash"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <ng-template #noItems>
          <div class="text-center py-5">
            <i class="bi bi-box2-heart text-muted display-1"></i>
            <p class="mt-3 text-muted">No items found in inventory.</p>
            <button routerLink="/add" class="btn btn-outline-primary btn-sm mt-2">Add your first item</button>
          </div>
        </ng-template>
      </div>
    </div>
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
    if (confirm('Are you sure you want to delete this item?')) {
      this.itemService.delete(id).subscribe(() => {
        this.loadItems();
      });
    }
  }
}