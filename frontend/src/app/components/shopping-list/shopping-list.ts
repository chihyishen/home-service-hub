import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ShoppingListService } from '../../services/shopping-list.service';
import { ShoppingListItemRequest, ShoppingListItemResponse } from '../../models/item.model';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { ToastModule } from 'primeng/toast';
import { TagModule } from 'primeng/tag';
import { MessageService } from 'primeng/api';

@Component({
  selector: 'app-shopping-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TableModule,
    ButtonModule,
    DialogModule,
    InputTextModule,
    InputNumberModule,
    ToastModule,
    TagModule
  ],
  providers: [MessageService],
  template: `
    <p-toast></p-toast>
    <div class="card p-3 p-lg-4">
      <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <h3 class="m-0">採買清單</h3>
        <div class="d-flex gap-2 flex-wrap">
          <p-button label="低庫存一鍵產生" icon="pi pi-magic" severity="warn" (onClick)="generateFromLowStock()"></p-button>
          <p-button label="手動新增" icon="pi pi-plus" (onClick)="openCreateDialog()"></p-button>
        </div>
      </div>

      <div class="d-flex gap-2 mb-4 flex-wrap">
        <p-button [outlined]="statusFilter() !== 'PENDING'" label="待購買" (onClick)="setStatus('PENDING')"></p-button>
        <p-button [outlined]="statusFilter() !== 'PURCHASED'" label="已購買" severity="success" (onClick)="setStatus('PURCHASED')"></p-button>
        <p-button [outlined]="statusFilter() !== 'SKIPPED'" label="略過" severity="secondary" (onClick)="setStatus('SKIPPED')"></p-button>
      </div>

      <p-table [value]="items()">
        <ng-template pTemplate="header">
          <tr>
            <th>品項</th>
            <th>建議數量</th>
            <th>來源</th>
            <th>狀態</th>
            <th>備註</th>
            <th style="width: 220px;">操作</th>
          </tr>
        </ng-template>
        <ng-template pTemplate="body" let-row>
          <tr>
            <td>{{ row.itemNameSnapshot }}</td>
            <td>{{ row.suggestedQuantity }}</td>
            <td>
              <p-tag [value]="row.source === 'LOW_STOCK_RULE' ? '低庫存規則' : '手動'" severity="secondary"></p-tag>
            </td>
            <td>
              <p-tag [value]="statusLabel(row.status)" [severity]="statusSeverity(row.status)"></p-tag>
            </td>
            <td>{{ row.note || '-' }}</td>
            <td>
              <div class="d-flex gap-1 flex-wrap">
                <p-button
                  *ngIf="row.status !== 'PURCHASED'"
                  icon="pi pi-check"
                  [text]="true"
                  severity="success"
                  (onClick)="updateStatus(row, 'PURCHASED')"
                ></p-button>
                <p-button
                  *ngIf="row.status !== 'SKIPPED'"
                  icon="pi pi-times"
                  [text]="true"
                  severity="secondary"
                  (onClick)="updateStatus(row, 'SKIPPED')"
                ></p-button>
                <p-button
                  *ngIf="row.status !== 'PENDING'"
                  icon="pi pi-replay"
                  [text]="true"
                  severity="info"
                  (onClick)="updateStatus(row, 'PENDING')"
                ></p-button>
                <p-button icon="pi pi-trash" [text]="true" severity="danger" (onClick)="remove(row.id)"></p-button>
              </div>
            </td>
          </tr>
        </ng-template>
      </p-table>
    </div>

    <p-dialog header="新增採買項目" [(visible)]="displayDialog" [modal]="true" [style]="{ width: '420px', maxWidth: '95vw' }">
      <div class="mb-3">
        <label class="d-block mb-2">品項名稱</label>
        <input pInputText class="w-100" [(ngModel)]="draft.itemNameSnapshot" />
      </div>
      <div class="mb-3">
        <label class="d-block mb-2">建議數量</label>
        <p-inputNumber [(ngModel)]="draft.suggestedQuantity" [min]="1" class="w-100"></p-inputNumber>
      </div>
      <div class="mb-3">
        <label class="d-block mb-2">備註</label>
        <input pInputText class="w-100" [(ngModel)]="draft.note" />
      </div>
      <ng-template pTemplate="footer">
        <p-button label="取消" [text]="true" (onClick)="displayDialog = false"></p-button>
        <p-button label="新增" (onClick)="createManual()" [disabled]="!canCreateManual()"></p-button>
      </ng-template>
    </p-dialog>
  `
})
export class ShoppingListComponent implements OnInit {
  private shoppingListService = inject(ShoppingListService);
  private messageService = inject(MessageService);

  items = signal<ShoppingListItemResponse[]>([]);
  statusFilter = signal<'PENDING' | 'PURCHASED' | 'SKIPPED'>('PENDING');
  displayDialog = false;
  draft: ShoppingListItemRequest = {
    itemNameSnapshot: '',
    suggestedQuantity: 1,
    source: 'MANUAL',
    status: 'PENDING',
    note: ''
  };

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.shoppingListService.getList(this.statusFilter()).subscribe({
      next: rows => this.items.set(rows),
      error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '無法載入採買清單' })
    });
  }

  setStatus(status: 'PENDING' | 'PURCHASED' | 'SKIPPED'): void {
    this.statusFilter.set(status);
    this.load();
  }

  generateFromLowStock(): void {
    this.shoppingListService.generateFromLowStock().subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: '成功', detail: '已從低庫存產生採買清單' });
        this.load();
      },
      error: err => this.messageService.add({ severity: 'error', summary: '錯誤', detail: err?.error?.message || '產生失敗' })
    });
  }

  openCreateDialog(): void {
    this.draft = {
      itemNameSnapshot: '',
      suggestedQuantity: 1,
      source: 'MANUAL',
      status: 'PENDING',
      note: ''
    };
    this.displayDialog = true;
  }

  createManual(): void {
    if (!this.canCreateManual()) {
      this.messageService.add({ severity: 'warn', summary: '提醒', detail: '請輸入品項名稱與正確數量' });
      return;
    }
    this.shoppingListService.create(this.draft).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: '成功', detail: '採買項目已新增' });
        this.displayDialog = false;
        this.load();
      },
      error: err => this.messageService.add({ severity: 'error', summary: '錯誤', detail: err?.error?.message || '新增失敗' })
    });
  }

  updateStatus(row: ShoppingListItemResponse, status: 'PENDING' | 'PURCHASED' | 'SKIPPED'): void {
    this.shoppingListService.update(row.id, { status }).subscribe({
      next: () => this.load(),
      error: err => this.messageService.add({ severity: 'error', summary: '錯誤', detail: err?.error?.message || '更新失敗' })
    });
  }

  remove(id: number): void {
    if (!confirm('確定刪除此採買項目？')) {
      return;
    }
    this.shoppingListService.delete(id).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: '成功', detail: '採買項目已刪除' });
        this.load();
      },
      error: err => this.messageService.add({ severity: 'error', summary: '錯誤', detail: err?.error?.message || '刪除失敗' })
    });
  }

  statusLabel(status: string): string {
    if (status === 'PENDING') return '待購買';
    if (status === 'PURCHASED') return '已購買';
    return '略過';
  }

  statusSeverity(status: string): 'warn' | 'success' | 'secondary' {
    if (status === 'PENDING') return 'warn';
    if (status === 'PURCHASED') return 'success';
    return 'secondary';
  }

  canCreateManual(): boolean {
    return !!this.draft.itemNameSnapshot?.trim() && (this.draft.suggestedQuantity ?? 0) > 0;
  }
}
