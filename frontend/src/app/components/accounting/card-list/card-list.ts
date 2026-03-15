import { Component, OnInit, inject, signal, ViewChild, computed, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AccountingService } from '../../../services/accounting.service';
import { CreditCard, PaymentMethod } from '../../../models/accounting.model';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { DialogModule } from 'primeng/dialog';
import { SelectModule } from 'primeng/select';
import { ToastModule } from 'primeng/toast';
import { MenuModule } from 'primeng/menu';
import { MessageService, MenuItem } from 'primeng/api';
import { Menu } from 'primeng/menu';
import { ListItemComponent } from '../../shared/list-item/list-item';

@Component({
  selector: 'app-card-list',
  imports: [
    CommonModule, 
    FormsModule, 
    TableModule, 
    ButtonModule, 
    InputTextModule, 
    InputNumberModule,
    DialogModule, 
    SelectModule,
    ToastModule,
    MenuModule,
    ListItemComponent
  ],
  providers: [MessageService],
  templateUrl: './card-list.html',
  styleUrl: './card-list.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CardListComponent implements OnInit {
  private accountingService = inject(AccountingService);
  private messageService = inject(MessageService);

  @ViewChild('menu') menu!: Menu;
  menuItems: MenuItem[] = [];

  cards = signal<CreditCard[]>([]);
  paymentMethods = signal<PaymentMethod[]>([]);
  displayDialog = false;
  isEdit = false;
  newCard: any = this.resetNewCard();

  cycleOptions = [
    { label: '帳單週期', value: 'BILLING_CYCLE' },
    { label: '日曆月 (1-31日)', value: 'CALENDAR_MONTH' }
  ];

  toolOptions = computed(() => 
    this.paymentMethods().map(m => ({ label: m.name, value: m.name }))
  );

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.accountingService.getCards().subscribe({
      next: (data) => this.cards.set(data),
      error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '無法載入卡片' })
    });
    this.accountingService.getPaymentMethods().subscribe({
        next: (data) => this.paymentMethods.set(data)
    });
  }

  resetNewCard() {
      return { 
          name: '', 
          billingDay: 1, 
          rewardCycleType: 'BILLING_CYCLE', 
          alertThreshold: 20000, 
          rewardRules: {},
          defaultPaymentMethod: 'Apple Pay' 
      };
  }

  showDialog() {
    this.newCard = this.resetNewCard();
    this.isEdit = false;
    this.displayDialog = true;
  }

  showMenu(event: MouseEvent, card: CreditCard) {
      this.menuItems = [
          { label: '編輯', icon: 'pi pi-pencil', command: () => this.editCard(card) },
          { separator: true },
          { label: '刪除', icon: 'pi pi-trash', styleClass: 'text-danger', command: () => this.deleteCard(card.id) }
      ];
      this.menu.toggle(event);
  }

  editCard(card: CreditCard) {
      this.isEdit = true;
      this.newCard = { ...card };
      this.displayDialog = true;
  }

  saveCard() {
    if (this.isEdit) {
        this.accountingService.updateCard(this.newCard.id, this.newCard).subscribe({
            next: () => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '卡片已更新' });
              this.displayDialog = false;
              this.loadData();
            },
            error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '更新失敗' })
          });
    } else {
        this.accountingService.createCard(this.newCard).subscribe({
            next: () => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '卡片已建立' });
              this.displayDialog = false;
              this.loadData();
            },
            error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '建立失敗' })
          });
    }
  }

  deleteCard(id: number) {
    if (confirm('確定要刪除此卡片嗎？')) {
      this.accountingService.deleteCard(id).subscribe({
        next: () => {
          this.messageService.add({ severity: 'success', summary: '成功', detail: '卡片已刪除' });
          this.loadData();
        },
        error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '刪除失敗' })
      });
    }
  }
}
