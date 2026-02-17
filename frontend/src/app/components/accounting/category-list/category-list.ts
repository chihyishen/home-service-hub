import { Component, OnInit, inject, signal, ViewChild } from '@angular/core';
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
  styleUrl: './category-list.scss'
})
export class CategoryListComponent implements OnInit {
  private accountingService = inject(AccountingService);
  private messageService = inject(MessageService);

  @ViewChild('menu') menu!: Menu;
  menuItems: MenuItem[] = [];

  categories = signal<Category[]>([]);

  displayCategoryDialog = false;
  isEditCategory = false;

  newCategory: any = { name: '', color: '#3498db' };

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
    this.newCategory = { name: '', color: '#3498db' };
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
}
