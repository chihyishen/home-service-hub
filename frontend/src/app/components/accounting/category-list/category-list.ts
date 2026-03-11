import { Component, OnInit, inject, signal, ViewChild, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AccountingService } from '../../../services/accounting.service';
import { Category, PaymentMethod } from '../../../models/accounting.model';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DialogModule } from 'primeng/dialog';
import { ToastModule } from 'primeng/toast';
import { TabsModule } from 'primeng/tabs';
import { TagModule } from 'primeng/tag';
import { MenuModule } from 'primeng/menu';
import { MessageService, MenuItem } from 'primeng/api';
import { Menu } from 'primeng/menu';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-category-list',
  standalone: true,
  imports: [
    CommonModule, 
    FormsModule, 
    TableModule, 
    ButtonModule, 
    InputTextModule, 
    DialogModule, 
    ToastModule,
    TagModule,
    MenuModule
  ],
  providers: [MessageService],
  templateUrl: './category-list.html',
  styleUrl: './category-list.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CategoryListComponent implements OnInit {
  private accountingService = inject(AccountingService);
  private messageService = inject(MessageService);

  @ViewChild('menu') menu!: Menu;
  menuItems: MenuItem[] = [];

  categories = signal<Category[]>([]);

  modernPalette: string[] = [
    '#0ea5e9',
    '#14b8a6',
    '#22c55e',
    '#84cc16',
    '#eab308',
    '#f97316',
    '#ef4444',
    '#ec4899',
    '#a855f7',
    '#6366f1',
    '#06b6d4',
    '#64748b'
  ];

  displayCategoryDialog = false;
  isEditCategory = false;

  newCategory: any = { name: '', color: '#0ea5e9' };

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.accountingService.getCategories().subscribe(data => this.categories.set(data));
  }

  showCategoryMenu(event: MouseEvent, cat: Category) {
      this.menuItems = [
          { label: '編輯', icon: 'pi pi-pencil', command: () => this.editCategory(cat) },
          { separator: true },
          { label: '刪除', icon: 'pi pi-trash', styleClass: 'text-danger', command: () => this.deleteCategory(cat.id) }
      ];
      this.menu.toggle(event);
  }

  showCategoryDialog() {
    this.newCategory = { name: '', color: this.modernPalette[0] };
    this.isEditCategory = false;
    this.displayCategoryDialog = true;
  }

  editCategory(cat: Category) {
      this.isEditCategory = true;
      this.newCategory = { ...cat };
      this.displayCategoryDialog = true;
  }

  saveCategory() {
    if (this.isEditCategory) {
        this.accountingService.updateCategory(this.newCategory.id, this.newCategory).subscribe({
            next: () => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '分類已更新' });
              this.displayCategoryDialog = false;
              this.loadData();
            },
            error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '更新失敗' })
          });
    } else {
        this.accountingService.createCategory(this.newCategory).subscribe({
            next: () => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '分類已建立' });
              this.displayCategoryDialog = false;
              this.loadData();
            },
            error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '建立失敗' })
          });
    }
  }

  deleteCategory(id: number) {
    if (confirm('確定要刪除此分類嗎？')) {
      this.accountingService.deleteCategory(id).subscribe({
        next: () => {
          this.messageService.add({ severity: 'success', summary: '成功', detail: '分類已刪除' });
          this.loadData();
        }
      });
    }
  }

  applyModernPalette() {
    const list = [...this.categories()].sort((a, b) => a.id - b.id);
    if (list.length === 0) return;

    const confirmed = confirm('將所有分類顏色更新為現代色票，確定要繼續嗎？');
    if (!confirmed) return;

    const requests = list.map((cat, idx) =>
      this.accountingService.updateCategory(cat.id, {
        name: cat.name,
        color: this.modernPalette[idx % this.modernPalette.length]
      })
    );

    forkJoin(requests).subscribe({
      next: () => {
        this.messageService.add({ severity: 'success', summary: '完成', detail: '分類色票已更新為現代風格' });
        this.loadData();
      },
      error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '更新色票失敗' })
    });
  }
}
