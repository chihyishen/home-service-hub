import { Component, OnInit, inject, signal, ChangeDetectionStrategy } from '@angular/core';
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
import { TooltipModule } from 'primeng/tooltip';
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
    TagModule,
    TooltipModule
  ],
  providers: [MessageService],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './shopping-list.html',
  styleUrl: './shopping-list.scss'
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
