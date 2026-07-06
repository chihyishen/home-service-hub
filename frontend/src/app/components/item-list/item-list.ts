import { Component, OnInit, inject, signal, computed, ChangeDetectionStrategy, DestroyRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Subject } from 'rxjs';
import { debounceTime } from 'rxjs/operators';
import { ItemService } from '../../services/item.service';
import { ShoppingListService } from '../../services/shopping-list.service';
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
import { TooltipModule } from 'primeng/tooltip';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { SkeletonModule } from 'primeng/skeleton';
import { MessageService, ConfirmationService } from 'primeng/api';

@Component({
  selector: 'app-item-list',
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
    ImageModule,
    TooltipModule,
    ConfirmDialogModule,
    SkeletonModule
  ],
  providers: [MessageService, ConfirmationService],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './item-list.html',
  styleUrl: './item-list.scss'
})
export class ItemListComponent implements OnInit {
  private itemService = inject(ItemService);
  private messageService = inject(MessageService);
  private confirmationService = inject(ConfirmationService);
  private shoppingListService = inject(ShoppingListService);
  private destroyRef = inject(DestroyRef);

  items = signal<ItemResponse[]>([]);
  history = signal<InventoryTransactionResponse[]>([]);
  isLoading = signal<boolean>(false);
  isError = signal<boolean>(false);
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
  private searchSubject = new Subject<string>();

  allCategories: string[] = [];
  filteredCategories: string[] = [];
  allLocations: string[] = [];
  filteredLocations: string[] = [];

  // Held image for create mode
  selectedFile: File | null = null;
  selectedFilePreview: string | null = null;

  groupedItems = computed(() => {
    const list = this.items();
    if (list.length === 0) {
      return [];
    }

    const groupsMap = new Map<string, ItemResponse[]>();
    for (const item of list) {
      const loc = item.location || '未知位置';
      if (!groupsMap.has(loc)) {
        groupsMap.set(loc, []);
      }
      groupsMap.get(loc)!.push(item);
    }

    const groups: { location: string; items: ItemResponse[] }[] = [];
    groupsMap.forEach((items, location) => {
      groups.push({ location, items });
    });

    groups.sort((a, b) => {
      if (a.location === '未知位置') return 1;
      if (b.location === '未知位置') return -1;
      return a.location.localeCompare(b.location, 'zh-TW');
    });

    return groups;
  });

  ngOnInit(): void {
    this.searchSubject.pipe(
      debounceTime(300),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(() => {
      this.loadItems();
    });

    this.loadItems();
    this.loadMetadata();
  }

  loadMetadata(): void {
    this.itemService.getCategories().subscribe(cats => this.allCategories = cats);
    this.itemService.getLocations().subscribe(locs => this.allLocations = locs);
  }

  loadItems(): void {
    this.isLoading.set(true);
    this.isError.set(false);
    this.itemService.getAllFiltered(this.searchKeyword, this.lowStockOnly).subscribe({
      next: data => {
        this.items.set(data);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
        this.isError.set(true);
        this.messageService.add({ severity: 'error', summary: '錯誤', detail: '無法載入物品清單' });
      }
    });
  }

  onSearchChange(): void {
    this.searchSubject.next(this.searchKeyword);
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
      note: ''
    };
  }

  showDialog() {
    this.newItem = this.resetNewItem();
    this.isEdit = false;
    this.cleanupImageSelection();
    this.displayDialog = true;
  }

  editItem(item: ItemResponse) {
    this.newItem = { ...item };
    this.isEdit = true;
    this.cleanupImageSelection();
    this.displayDialog = true;
  }

  cleanupImageSelection() {
    this.selectedFile = null;
    if (this.selectedFilePreview) {
      URL.revokeObjectURL(this.selectedFilePreview);
      this.selectedFilePreview = null;
    }
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
      next: (createdItem) => {
        this.messageService.add({ severity: 'success', summary: '成功', detail: '物品已建立' });
        this.displayDialog = false;
        
        if (this.selectedFile && createdItem?.id) {
          this.itemService.uploadImage(createdItem.id, this.selectedFile).subscribe({
            next: () => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '圖片上傳成功' });
              this.loadItems();
              this.cleanupImageSelection();
            },
            error: () => {
              this.messageService.add({ severity: 'error', summary: '錯誤', detail: '圖片上傳失敗' });
              this.loadItems();
              this.cleanupImageSelection();
            }
          });
        } else {
          this.loadItems();
          this.cleanupImageSelection();
        }
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
    } else {
      this.selectedFile = file;
      if (this.selectedFilePreview) {
        URL.revokeObjectURL(this.selectedFilePreview);
      }
      this.selectedFilePreview = URL.createObjectURL(file);
    }
  }

  consumeOne(item: ItemResponse) {
    const payload: InventoryTransactionRequest = {
      type: 'CONSUME',
      source: 'MANUAL',
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
      source: 'MANUAL',
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
    this.confirmationService.confirm({
      message: '確定要刪除此物品嗎？',
      header: '確認刪除',
      icon: 'pi pi-exclamation-triangle',
      acceptIcon: 'none',
      rejectIcon: 'none',
      rejectButtonStyleClass: 'p-button-text',
      accept: () => {
        this.itemService.delete(id).subscribe({
          next: () => {
            this.messageService.add({ severity: 'success', summary: '成功', detail: '物品已刪除' });
            this.loadItems();
          },
          error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '刪除失敗' })
        });
      }
    });
  }

  addLowStockToShoppingList(): void {
    this.shoppingListService.generateFromLowStock().subscribe({
      next: (items) => {
        const count = items.length;
        this.messageService.add({
          severity: 'success',
          summary: '成功',
          detail: `已將 ${count} 項低庫存物品加入購物清單`
        });
      },
      error: () => {
        this.messageService.add({
          severity: 'error',
          summary: '錯誤',
          detail: '無法將低庫存物品加入購物清單'
        });
      }
    });
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
    if (!this.newItem.name || qty == null || qty < 0) {
      return false;
    }
    if (min != null && min < 0) {
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

