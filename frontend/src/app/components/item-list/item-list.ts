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
import { AutoCompleteModule } from 'primeng/autocomplete';
import { FileUploadModule } from 'primeng/fileupload';
import { ImageModule } from 'primeng/image';
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
    MenuModule,
    AutoCompleteModule,
    FileUploadModule,
    ImageModule
  ],
  providers: [MessageService],
  template: `
    <p-toast></p-toast>
    <div class="card p-3 p-lg-4">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
        <h3 class="m-0">庫存管理</h3>
        <div class="d-flex gap-2 w-100-mobile">
            <input pInputText type="text" [(ngModel)]="searchKeyword" (ngModelChange)="loadItems()" placeholder="搜尋物品名稱或備註..." class="flex-grow-1" />
            <p-button label="新增物品" icon="pi pi-plus" (onClick)="showDialog()" styleClass="w-100-mobile"></p-button>
        </div>
      </div>

      <p-table [value]="items()" [rows]="10" [paginator]="true" responsiveLayout="stack" [breakpoint]="'960px'">
        <ng-template pTemplate="header">
          <tr>
            <th style="width: 80px">圖片</th>
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
              <span class="p-column-title fw-bold">圖片</span>
              <p-image *ngIf="item.imageUrl" [src]="item.imageUrl" [preview]="true" width="50" class="vertical-align-middle"></p-image>
              <i *ngIf="!item.imageUrl" class="pi pi-image text-muted" style="font-size: 1.5rem"></i>
            </td>
            <td>
              <span class="p-column-title fw-bold">名稱</span>
              <div class="fw-bold">{{ item.name }}</div>
              <small class="text-muted" *ngIf="item.note">{{ item.note }}</small>
            </td>
            <td>
                <span class="p-column-title fw-bold">類別</span>
                <p-tag [value]="item.category" severity="secondary"></p-tag>
            </td>
            <td>
              <span class="p-column-title fw-bold">位置</span>
              {{ item.location }}
            </td>
            <td>
              <span class="p-column-title fw-bold">數量</span>
              <p-tag [severity]="getQuantitySeverity(item.quantity)" [value]="item.quantity.toString()"></p-tag>
            </td>
            <td>
              <span class="p-column-title fw-bold">操作</span>
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

      <p-dialog [header]="isEdit ? '編輯物品' : '新增物品'" [(visible)]="displayDialog" [modal]="true" 
                [style]="{width: '450px', maxWidth: '95vw'}" [dismissableMask]="true">
        <div class="flex flex-column gap-3 mt-2">
          <div class="field">
            <label class="d-block mb-2">名稱</label>
            <input pInputText [(ngModel)]="newItem.name" class="w-100" placeholder="例如：電池" />
          </div>
          <div class="row g-2">
            <div class="col-12 col-md-6">
                <label class="d-block mb-2">類別</label>
                <p-autoComplete [(ngModel)]="newItem.category" [suggestions]="filteredCategories" (completeMethod)="filterCategories($event)" [dropdown]="true" styleClass="w-100" placeholder="例如：耗材"></p-autoComplete>
            </div>
            <div class="col-12 col-md-6">
                <label class="d-block mb-2">位置</label>
                <p-autoComplete [(ngModel)]="newItem.location" [suggestions]="filteredLocations" (completeMethod)="filterLocations($event)" [dropdown]="true" styleClass="w-100" placeholder="例如：抽屜"></p-autoComplete>
            </div>
          </div>
          <div class="field">
            <label class="d-block mb-2">數量</label>
            <p-inputNumber [(ngModel)]="newItem.quantity" [min]="0" class="w-100"></p-inputNumber>
          </div>
          <div class="field" *ngIf="isEdit">
            <label class="d-block mb-2">圖片</label>
            <div class="d-flex align-items-center gap-3">
                <p-image *ngIf="newItem.imageUrl" [src]="newItem.imageUrl" [preview]="true" width="100"></p-image>
                <p-fileUpload mode="basic" chooseLabel="上傳圖片" name="file" accept="image/*" [auto]="true" [customUpload]="true" (uploadHandler)="onUpload($event)"></p-fileUpload>
            </div>
          </div>
          <div class="alert alert-info mt-2" *ngIf="!isEdit">
            <i class="pi pi-info-circle me-2"></i> 請先儲存物品，再上傳圖片。
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
  
  // Search & Autocomplete
  searchKeyword: string = '';
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
    this.itemService.getAll(this.searchKeyword).subscribe({
      next: (data) => this.items.set(data),
      error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '無法載入物品清單' })
    });
  }
  
  filterCategories(event: any) {
    const query = event.query.toLowerCase();
    this.filteredCategories = this.allCategories.filter(c => c.toLowerCase().includes(query));
  }

  filterLocations(event: any) {
    const query = event.query.toLowerCase();
    this.filteredLocations = this.allLocations.filter(l => l.toLowerCase().includes(query));
  }

  onUpload(event: any) {
    const file = event.files[0];
    if (this.isEdit && this.newItem.id) {
        this.itemService.uploadImage(this.newItem.id, file).subscribe({
            next: (updatedItem) => {
                this.newItem.imageUrl = updatedItem.imageUrl;
                this.messageService.add({ severity: 'success', summary: '成功', detail: '圖片上傳成功' });
                this.loadItems();
            },
            error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '圖片上傳失敗' })
        });
    }
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
