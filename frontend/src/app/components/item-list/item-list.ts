import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ItemService } from '../../services/item.service';
import {
  InventoryTransactionRequest,
  InventoryTransactionResponse,
  ItemRequest,
  ItemResponse
} from '../../models/item.model';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { TextareaModule } from 'primeng/textarea';
import { ToastModule } from 'primeng/toast';
import { TagModule } from 'primeng/tag';
import { AutoCompleteModule } from 'primeng/autocomplete';
import { FileUploadModule } from 'primeng/fileupload';
import { ImageModule } from 'primeng/image';
import { MessageService } from 'primeng/api';

@Component({
  selector: 'app-item-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TableModule,
    ButtonModule,
    DialogModule,
    InputTextModule,
    InputNumberModule,
    TextareaModule,
    ToastModule,
    TagModule,
    AutoCompleteModule,
    FileUploadModule,
    ImageModule
  ],
  providers: [MessageService],
  template: `
    <p-toast></p-toast>
    <div class="card p-3 p-lg-4">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-3">
        <h3 class="m-0">庫存管理</h3>
        <div class="d-flex gap-2 w-100-mobile">
          <input
            pInputText
            type="text"
            [(ngModel)]="searchKeyword"
            (ngModelChange)="loadItems()"
            placeholder="搜尋物品名稱或備註..."
            class="flex-grow-1"
          />
          <p-button label="新增物品" icon="pi pi-plus" (onClick)="showDialog()" styleClass="w-100-mobile"></p-button>
        </div>
      </div>

      <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-4">
        <div class="form-check m-0 low-stock-toggle">
          <input
            class="form-check-input"
            type="checkbox"
            id="lowStockOnly"
            [(ngModel)]="lowStockOnly"
            (change)="loadItems()"
          />
          <label class="form-check-label low-stock-label" for="lowStockOnly">只看低庫存</label>
        </div>
      </div>

      <p-table [value]="items()" [rows]="10" [paginator]="true" responsiveLayout="stack" [breakpoint]="'960px'">
        <ng-template pTemplate="header">
          <tr>
            <th style="width: 80px">圖片</th>
            <th>名稱</th>
            <th>類別</th>
            <th>位置</th>
            <th>狀態</th>
            <th>庫存</th>
            <th>門檻/目標</th>
            <th style="width: 340px">操作</th>
          </tr>
        </ng-template>
        <ng-template pTemplate="body" let-item>
          <tr>
            <td>
              <span class="p-column-title fw-bold">圖片</span>
              <p-image *ngIf="item.imageUrl" [src]="item.imageUrl" [preview]="true" width="50" class="vertical-align-middle"></p-image>
              <i *ngIf="!item.imageUrl" class="pi pi-image text-muted" style="font-size: 1.5rem"></i>
            </td>
            <td>
              <span class="p-column-title fw-bold">名稱</span>
              <div class="fw-bold">{{ item.name }}</div>
            </td>
            <td>
              <span class="p-column-title fw-bold">類別</span>
              <p-tag [value]="item.category || '-'" severity="secondary"></p-tag>
            </td>
            <td>
              <span class="p-column-title fw-bold">位置</span>
              {{ item.location || '-' }}
            </td>
            <td>
              <span class="p-column-title fw-bold">狀態</span>
              <p-tag [severity]="getStockStatusSeverity(item)" [value]="getStockStatusLabel(item)"></p-tag>
            </td>
            <td>
              <span class="p-column-title fw-bold">庫存</span>
              <b>{{ item.quantity }}</b>
            </td>
            <td>
              <span class="p-column-title fw-bold">門檻/目標</span>
              {{ item.minQuantity ?? '-' }} / {{ item.targetQuantity ?? '-' }}
            </td>
            <td>
              <span class="p-column-title fw-bold">操作</span>
              <div class="d-flex gap-1 flex-nowrap align-items-center action-buttons">
                <p-button icon="pi pi-minus" [rounded]="true" [text]="true" severity="warn" (onClick)="consumeOne(item)"></p-button>
                <p-button icon="pi pi-plus" [rounded]="true" [text]="true" severity="success" (onClick)="openQuickAction(item, 'RESTOCK')"></p-button>
                <p-button icon="pi pi-refresh" [rounded]="true" [text]="true" severity="info" (onClick)="openQuickAction(item, 'ADJUST')"></p-button>
                <p-button icon="pi pi-history" [rounded]="true" [text]="true" severity="secondary" (onClick)="openHistory(item)"></p-button>
                <p-button icon="pi pi-pencil" [rounded]="true" [text]="true" severity="secondary" (onClick)="editItem(item)"></p-button>
                <p-button icon="pi pi-trash" [rounded]="true" [text]="true" severity="danger" (onClick)="deleteItem(item.id)"></p-button>
              </div>
            </td>
          </tr>
        </ng-template>
      </p-table>

      <p-dialog [header]="isEdit ? '編輯物品' : '新增物品'" [(visible)]="displayDialog" [modal]="true"
                [style]="{width: '560px', maxWidth: '95vw'}" [dismissableMask]="true">
        <div class="row g-3 mt-1">
          <div class="col-12">
            <label class="d-block mb-2">名稱</label>
            <input pInputText [(ngModel)]="newItem.name" class="w-100" placeholder="例如：衛生紙" />
          </div>
          <div class="col-12 col-md-6">
            <label class="d-block mb-2">類別</label>
            <p-autoComplete [(ngModel)]="newItem.category" [suggestions]="filteredCategories" (completeMethod)="filterCategories($event)" [dropdown]="true" styleClass="w-100"></p-autoComplete>
          </div>
          <div class="col-12 col-md-6">
            <label class="d-block mb-2">位置</label>
            <p-autoComplete [(ngModel)]="newItem.location" [suggestions]="filteredLocations" (completeMethod)="filterLocations($event)" [dropdown]="true" styleClass="w-100"></p-autoComplete>
          </div>
          <div class="col-12 col-md-6">
            <label class="d-block mb-2">數量</label>
            <p-inputNumber [(ngModel)]="newItem.quantity" [min]="0" class="w-100"></p-inputNumber>
          </div>
          <div class="col-12 col-md-6">
            <label class="d-block mb-2">低庫存門檻</label>
            <p-inputNumber [(ngModel)]="newItem.minQuantity" [min]="0" class="w-100"></p-inputNumber>
          </div>
          <div class="col-12">
            <label class="d-block mb-2">理想庫存量</label>
            <p-inputNumber [(ngModel)]="newItem.targetQuantity" [min]="0" class="w-100"></p-inputNumber>
          </div>
          <div class="col-12">
            <label class="d-block mb-2">備註</label>
            <textarea pTextarea [(ngModel)]="newItem.note" rows="3" class="w-100"></textarea>
          </div>
        </div>

        <div class="field mt-3" *ngIf="isEdit">
          <label class="d-block mb-2">圖片</label>
          <div class="d-flex align-items-center gap-3">
            <p-image *ngIf="newItem.imageUrl" [src]="newItem.imageUrl" [preview]="true" width="100"></p-image>
            <p-fileUpload mode="basic" chooseLabel="上傳圖片" name="file" accept="image/*" [auto]="true" [customUpload]="true" (uploadHandler)="onUpload($event)"></p-fileUpload>
          </div>
        </div>

        <ng-template pTemplate="footer">
          <p-button label="取消" icon="pi pi-times" [text]="true" (onClick)="displayDialog = false"></p-button>
          <p-button label="儲存" icon="pi pi-check" (onClick)="saveItem()" [disabled]="!canSaveItem()"></p-button>
        </ng-template>
      </p-dialog>

      <p-dialog [header]="quickActionTitle" [(visible)]="displayActionDialog" [modal]="true" [style]="{width: '420px', maxWidth: '95vw'}">
        <div class="mb-2"><b>{{ selectedItem?.name }}</b></div>
        <div class="text-muted mb-3">目前數量：{{ selectedItem?.quantity }}</div>
        <div class="mb-3" *ngIf="actionType !== 'ADJUST'">
          <label class="d-block mb-2">異動量</label>
          <p-inputNumber [(ngModel)]="actionAmount" [min]="1" class="w-100"></p-inputNumber>
        </div>
        <div class="mb-3" *ngIf="actionType === 'ADJUST'">
          <label class="d-block mb-2">盤點後實際數量</label>
          <p-inputNumber [(ngModel)]="actualAmount" [min]="0" class="w-100"></p-inputNumber>
        </div>
        <div class="mb-3">
          <label class="d-block mb-2">原因（選填）</label>
          <input pInputText [(ngModel)]="actionReason" class="w-100" />
        </div>
        <ng-template pTemplate="footer">
          <p-button label="取消" [text]="true" (onClick)="displayActionDialog = false"></p-button>
          <p-button label="送出" (onClick)="submitAction()"></p-button>
        </ng-template>
      </p-dialog>

      <p-dialog header="異動歷史" [(visible)]="displayHistoryDialog" [modal]="true" [style]="{width: '760px', maxWidth: '95vw'}">
        <p-table [value]="history()">
          <ng-template pTemplate="header">
            <tr>
              <th>時間</th>
              <th>類型</th>
              <th>前</th>
              <th>後</th>
              <th>差額</th>
              <th>原因</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-row>
            <tr>
              <td>{{ row.occurredAt | date: 'yyyy/MM/dd HH:mm' }}</td>
              <td>{{ row.type }}</td>
              <td>{{ row.beforeQuantity }}</td>
              <td>{{ row.afterQuantity }}</td>
              <td>{{ row.deltaQuantity }}</td>
              <td>{{ row.reason || '-' }}</td>
            </tr>
          </ng-template>
        </p-table>
      </p-dialog>
    </div>
  `,
  styles: [`
    :host ::ng-deep {
      .p-tag {
        font-weight: 500;
      }

      .w-100-mobile {
        @media (max-width: 576px) {
          width: 100%;
        }
      }

      .p-autocomplete {
        width: 100%;
      }

      .action-buttons {
        white-space: nowrap;
      }

      .low-stock-label {
        color: var(--p-text-color, inherit);
        font-weight: 600;
      }
    }
  `]
})
export class ItemListComponent implements OnInit {
  private itemService = inject(ItemService);
  private messageService = inject(MessageService);

  items = signal<ItemResponse[]>([]);
  history = signal<InventoryTransactionResponse[]>([]);
  displayDialog = false;
  displayActionDialog = false;
  displayHistoryDialog = false;
  isEdit = false;
  lowStockOnly = false;

  selectedItem: ItemResponse | null = null;
  actionType: 'RESTOCK' | 'ADJUST' = 'RESTOCK';
  quickActionTitle = '';
  actionAmount = 1;
  actualAmount = 0;
  actionReason = '';

  newItem: ItemRequest & Partial<ItemResponse> = this.resetNewItem();
  searchKeyword = '';
  allCategories: string[] = [];
  filteredCategories: string[] = [];
  allLocations: string[] = [];
  filteredLocations: string[] = [];

  ngOnInit(): void {
    this.loadItems();
    this.loadMetadata();
  }

  loadMetadata(): void {
    this.itemService.getCategories().subscribe(cats => this.allCategories = cats);
    this.itemService.getLocations().subscribe(locs => this.allLocations = locs);
  }

  loadItems(): void {
    this.itemService.getAll(this.searchKeyword, this.lowStockOnly).subscribe({
      next: data => this.items.set(data),
      error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '無法載入物品清單' })
    });
  }

  filterCategories(event: { query: string }) {
    const query = event.query.toLowerCase();
    this.filteredCategories = this.allCategories.filter(c => c.toLowerCase().includes(query));
  }

  filterLocations(event: { query: string }) {
    const query = event.query.toLowerCase();
    this.filteredLocations = this.allLocations.filter(l => l.toLowerCase().includes(query));
  }

  resetNewItem(): ItemRequest & Partial<ItemResponse> {
    return {
      name: '',
      category: '',
      location: '',
      quantity: 1,
      minQuantity: null,
      targetQuantity: null,
      isConsumable: true,
      status: 'ACTIVE',
      note: ''
    };
  }

  showDialog() {
    this.newItem = this.resetNewItem();
    this.isEdit = false;
    this.displayDialog = true;
  }

  editItem(item: ItemResponse) {
    this.newItem = { ...item };
    this.isEdit = true;
    this.displayDialog = true;
  }

  saveItem() {
    if (!this.canSaveItem()) {
      this.messageService.add({ severity: 'warn', summary: '提醒', detail: '請檢查名稱、數量與門檻欄位' });
      return;
    }

    const payload: ItemRequest = {
      name: this.newItem.name,
      category: this.newItem.category || '',
      location: this.newItem.location || '',
      quantity: this.newItem.quantity,
      minQuantity: this.newItem.minQuantity ?? null,
      targetQuantity: this.newItem.targetQuantity ?? null,
      isConsumable: this.newItem.isConsumable ?? true,
      status: this.newItem.status || 'ACTIVE',
      note: this.newItem.note || '',
      imageUrl: this.newItem.imageUrl || undefined
    };

    if (this.isEdit && this.newItem.id) {
      this.itemService.update(this.newItem.id, payload).subscribe({
        next: () => {
          this.messageService.add({ severity: 'success', summary: '成功', detail: '物品已更新' });
          this.displayDialog = false;
          this.loadItems();
        },
        error: err => this.messageService.add({ severity: 'error', summary: '錯誤', detail: err?.error?.message || '更新失敗' })
      });
      return;
    }

    this.itemService.create(payload).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: '成功', detail: '物品已建立' });
        this.displayDialog = false;
        this.loadItems();
      },
      error: err => this.messageService.add({ severity: 'error', summary: '錯誤', detail: err?.error?.message || '建立失敗' })
    });
  }

  onUpload(event: { files: File[] }) {
    const file = event.files[0];
    if (this.isEdit && this.newItem.id) {
      this.itemService.uploadImage(this.newItem.id, file).subscribe({
        next: updatedItem => {
          this.newItem.imageUrl = updatedItem.imageUrl;
          this.messageService.add({ severity: 'success', summary: '成功', detail: '圖片上傳成功' });
          this.loadItems();
        },
        error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '圖片上傳失敗' })
      });
    }
  }

  consumeOne(item: ItemResponse) {
    const payload: InventoryTransactionRequest = {
      type: 'CONSUME',
      deltaQuantity: 1,
      operatorName: 'web-ui',
      reason: '快速使用 -1'
    };
    this.submitTransaction(item.id, payload, '扣庫成功');
  }

  openQuickAction(item: ItemResponse, type: 'RESTOCK' | 'ADJUST') {
    this.selectedItem = item;
    this.actionType = type;
    this.quickActionTitle = type === 'RESTOCK' ? '快速補貨' : '盤點修正';
    this.actionAmount = 1;
    this.actualAmount = item.quantity;
    this.actionReason = '';
    this.displayActionDialog = true;
  }

  submitAction() {
    if (!this.selectedItem) {
      return;
    }

    const payload: InventoryTransactionRequest = {
      type: this.actionType,
      operatorName: 'web-ui',
      reason: this.actionReason || undefined
    };

    if (this.actionType === 'RESTOCK') {
      payload.deltaQuantity = this.actionAmount;
    } else {
      payload.actualQuantity = this.actualAmount;
    }

    const successMessage = this.actionType === 'RESTOCK' ? '補貨成功' : '盤點修正成功';
    this.submitTransaction(this.selectedItem.id, payload, successMessage, () => {
      this.displayActionDialog = false;
    });
  }

  openHistory(item: ItemResponse) {
    this.itemService.getTransactions(item.id, 50).subscribe({
      next: rows => {
        this.history.set(rows);
        this.displayHistoryDialog = true;
      },
      error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '無法載入異動歷史' })
    });
  }

  deleteItem(id: number): void {
    if (confirm('確定要刪除此物品嗎？')) {
      this.itemService.delete(id).subscribe({
        next: () => {
          this.messageService.add({ severity: 'success', summary: '成功', detail: '物品已刪除' });
          this.loadItems();
        },
        error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '刪除失敗' })
      });
    }
  }

  getStockStatusLabel(item: ItemResponse): string {
    if (item.stockStatus === 'OUT') return '缺貨';
    if (item.stockStatus === 'LOW') return '低庫存';
    return '正常';
  }

  getStockStatusSeverity(item: ItemResponse): 'danger' | 'warn' | 'success' {
    if (item.stockStatus === 'OUT') return 'danger';
    if (item.stockStatus === 'LOW') return 'warn';
    return 'success';
  }

  canSaveItem(): boolean {
    const qty = this.newItem.quantity;
    const min = this.newItem.minQuantity;
    const target = this.newItem.targetQuantity;
    if (!this.newItem.name || qty == null || qty < 0) {
      return false;
    }
    if (min != null && min < 0) {
      return false;
    }
    if (target != null && target < 0) {
      return false;
    }
    return true;
  }

  private submitTransaction(
    itemId: number,
    payload: InventoryTransactionRequest,
    successMessage: string,
    callback?: () => void
  ) {
    this.itemService.createTransaction(itemId, payload).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: '成功', detail: successMessage });
        this.loadItems();
        callback?.();
      },
      error: err => this.messageService.add({ severity: 'error', summary: '錯誤', detail: err?.error?.message || '操作失敗' })
    });
  }
}
