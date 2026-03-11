import { Component, OnInit, inject, signal, ViewChild, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AccountingService } from '../../../services/accounting.service';
import { PaymentMethod } from '../../../models/accounting.model';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { DialogModule } from 'primeng/dialog';
import { ToastModule } from 'primeng/toast';
import { TagModule } from 'primeng/tag';
import { MenuModule } from 'primeng/menu';
import { MessageService, MenuItem } from 'primeng/api';
import { Menu } from 'primeng/menu';

@Component({
  selector: 'app-payment-method-list',
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
  templateUrl: './payment-method-list.html',
  styleUrl: './payment-method-list.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PaymentMethodListComponent implements OnInit {
  private accountingService = inject(AccountingService);
  private messageService = inject(MessageService);

  @ViewChild('menu') menu!: Menu;
  menuItems: MenuItem[] = [];

  paymentMethods = signal<PaymentMethod[]>([]);

  displayPMDialog = false;
  isEditPM = false;

  newPM: any = { name: '' };

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.accountingService.getPaymentMethods().subscribe(data => this.paymentMethods.set(data));
  }

  showPMMenu(event: MouseEvent, pm: PaymentMethod) {
      this.menuItems = [
          { label: '編輯', icon: 'pi pi-pencil', command: () => this.editPM(pm) },
          { separator: true },
          { label: '刪除', icon: 'pi pi-trash', styleClass: 'text-danger', command: () => this.deletePM(pm.id) }
      ];
      this.menu.toggle(event);
  }

  showPMDialog() {
    this.newPM = { name: '' };
    this.isEditPM = false;
    this.displayPMDialog = true;
  }

  editPM(pm: PaymentMethod) {
      this.isEditPM = true;
      this.newPM = { ...pm };
      this.displayPMDialog = true;
  }

  savePM() {
    if (this.isEditPM) {
        this.accountingService.updatePaymentMethod(this.newPM.id, this.newPM).subscribe({
            next: () => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '支付方式已更新' });
              this.displayPMDialog = false;
              this.loadData();
            },
            error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '更新失敗' })
          });
    } else {
        this.accountingService.createPaymentMethod(this.newPM).subscribe({
            next: () => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '支付方式已建立' });
              this.displayPMDialog = false;
              this.loadData();
            },
            error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '建立失敗' })
          });
    }
  }

  deletePM(id: number) {
    if (confirm('確定要刪除此支付方式嗎？')) {
      this.accountingService.deletePaymentMethod(id).subscribe({
        next: () => {
          this.messageService.add({ severity: 'success', summary: '成功', detail: '支付方式已刪除' });
          this.loadData();
        }
      });
    }
  }
}
