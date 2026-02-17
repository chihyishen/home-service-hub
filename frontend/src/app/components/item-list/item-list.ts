import { Component, OnInit, inject, signal, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ItemService } from '../../services/item.service';
import { ItemResponse } from '../../models/item.model';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { TextareaModule } from 'primeng/textarea';
import { ToastModule } from 'primeng/toast';
import { TagModule } from 'primeng/tag';
import { MenuModule } from 'primeng/menu';
import { MessageService, MenuItem } from 'primeng/api';
import { Menu } from 'primeng/menu';

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
    MenuModule
  ],
  providers: [MessageService],
  template: `
    <p-toast></p-toast>
    <div class="card p-4">
      <div class="d-flex justify-content-between align-items-center mb-4">
        <h3 class="m-0">庫存管理</h3>
        <p-button label="新增物品" icon="pi pi-plus" (onClick)="showDialog()"></p-button>
      </div>

      <p-table [value]="items()" [rows]="10" [paginator]="true" responsiveLayout="scroll">
        <ng-template pTemplate="header">
          <tr>
            <th pSortableColumn="name">名稱 <p-sortIcon field="name"></p-sortIcon></th>
            <th pSortableColumn="category">類別 <p-sortIcon field="category"></p-sortIcon></th>
            <th pSortableColumn="location">位置 <p-sortIcon field="location"></p-sortIcon></th>
            <th pSortableColumn="quantity">數量 <p-sortIcon field="quantity"></p-sortIcon></th>
            <th style="width: 100px">操作</th>
          </tr>
        </ng-template>
        <ng-template pTemplate="body" let-item>
          <tr>
            <td>
              <div class="fw-bold">{{ item.name }}</div>
              <small class="text-muted" *ngIf="item.note">{{ item.note }}</small>
            </td>
            <td>
                <p-tag [value]="item.category" severity="secondary"></p-tag>
            </td>
            <td>{{ item.location }}</td>
            <td>
              <p-tag [severity]="getQuantitySeverity(item.quantity)" [value]="item.quantity.toString()"></p-tag>
            </td>
            <td>
              <p-button icon="pi pi-ellipsis-v" [text]="true" [rounded]="true" severity="secondary" (click)="showMenu($event, item)"></p-button>
            </td>
          </tr>
        </ng-template>
        <ng-template pTemplate="emptymessage">
            <tr>
                <td colspan="5" class="text-center p-4">目前沒有任何物品。</td>
            </tr>
        </ng-template>
      </p-table>

      <p-menu #menu [model]="menuItems" [popup]="true" appendTo="body"></p-menu>

      <p-dialog [header]="isEdit ? '編輯物品' : '新增物品'" [(visible)]="displayDialog" [modal]="true" [style]="{width: '35vw'}" [dismissableMask]="true">
        <div class="flex flex-column gap-3 mt-2">
          <div class="field">
            <label class="d-block mb-2">名稱</label>
            <input pInputText [(ngModel)]="newItem.name" class="w-100" placeholder="例如：電池" />
          </div>
          <div class="row">
            <div class="col-6">
                <label class="d-block mb-2">類別</label>
                <input pInputText [(ngModel)]="newItem.category" class="w-100" placeholder="例如：耗材" />
            </div>
            <div class="col-6">
                <label class="d-block mb-2">位置</label>
                <input pInputText [(ngModel)]="newItem.location" class="w-100" placeholder="例如：抽屜" />
            </div>
          </div>
          <div class="field">
            <label class="d-block mb-2">數量</label>
            <p-inputNumber [(ngModel)]="newItem.quantity" [min]="0" class="w-100"></p-inputNumber>
          </div>
          <div class="field">
            <label class="d-block mb-2">備註</label>
            <textarea pTextarea [(ngModel)]="newItem.note" rows="3" class="w-100"></textarea>
          </div>
        </div>
        <ng-template pTemplate="footer">
          <p-button label="取消" icon="pi pi-times" [text]="true" (onClick)="displayDialog = false"></p-button>
          <p-button label="儲存" icon="pi pi-check" (onClick)="saveItem()" [disabled]="!newItem.name"></p-button>
        </ng-template>
      </p-dialog>
    </div>
  `,
  styles: [`
    :host ::ng-deep .p-tag {
        font-weight: 500;
    }
  `]
})
export class ItemListComponent implements OnInit {
  private itemService = inject(ItemService);
  private messageService = inject(MessageService);

  @ViewChild('menu') menu!: Menu;
  menuItems: MenuItem[] = [];

  items = signal<ItemResponse[]>([]);
  displayDialog = false;
  isEdit = false;
  
  newItem: any = this.resetNewItem();

  ngOnInit(): void {
    this.loadItems();
  }

  loadItems(): void {
    this.itemService.getAll().subscribe({
      next: (data) => this.items.set(data),
      error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '無法載入物品清單' })
    });
  }

  showMenu(event: MouseEvent, item: ItemResponse) {
      this.menuItems = [
          { label: '編輯', icon: 'pi pi-pencil', command: () => this.editItem(item) },
          { separator: true },
          { label: '刪除', icon: 'pi pi-trash', styleClass: 'text-danger', command: () => this.deleteItem(item.id) }
      ];
      this.menu.toggle(event);
  }

  resetNewItem() {
    return {
      name: '',
      category: '',
      location: '',
      quantity: 1,
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
    if (this.isEdit) {
      this.itemService.update(this.newItem.id, this.newItem).subscribe({
        next: () => {
          this.messageService.add({ severity: 'success', summary: '成功', detail: '物品已更新' });
          this.displayDialog = false;
          this.loadItems();
        },
        error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '更新失敗' })
      });
    } else {
      this.itemService.create(this.newItem).subscribe({
        next: () => {
          this.messageService.add({ severity: 'success', summary: '成功', detail: '物品已建立' });
          this.displayDialog = false;
          this.loadItems();
        },
        error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '建立失敗' })
      });
    }
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

  getQuantitySeverity(qty: number): "success" | "danger" | "warn" | undefined {
      if (qty <= 0) return 'danger';
      if (qty <= 2) return 'warn';
      return 'success';
  }
}
