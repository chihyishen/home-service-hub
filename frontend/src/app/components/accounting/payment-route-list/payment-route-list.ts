import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AccountingService } from '../../../services/accounting.service';
import { PaymentRoute, CreditCard, PaymentMethod } from '../../../models/accounting.model';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { SelectModule } from 'primeng/select';
import { TagModule } from 'primeng/tag';
import { DialogModule } from 'primeng/dialog';
import { ToastModule } from 'primeng/toast';
import { MessageService } from 'primeng/api';
import { forkJoin } from 'rxjs';

@Component({
  selector: 'app-payment-route-list',
  standalone: true,
  imports: [
    CommonModule, 
    FormsModule, 
    TableModule, 
    ButtonModule, 
    SelectModule,
    TagModule,
    DialogModule, 
    ToastModule
  ],
  providers: [MessageService],
  templateUrl: './payment-route-list.html',
  styleUrl: './payment-route-list.scss'
})
export class PaymentRouteListComponent implements OnInit {
  private accountingService = inject(AccountingService);
  private messageService = inject(MessageService);

  routes = signal<PaymentRoute[]>([]);
  cards = signal<CreditCard[]>([]);
  paymentMethods = signal<PaymentMethod[]>([]);

  displayDialog = false;
  newRoute: any = { methodName: '', cardId: null };

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    forkJoin({
        routes: this.accountingService.getPaymentRoutes(),
        cards: this.accountingService.getCards(),
        methods: this.accountingService.getPaymentMethods()
    }).subscribe(({ routes, cards, methods }) => {
        this.routes.set(routes);
        this.cards.set(cards);
        this.paymentMethods.set(methods);
    });
  }

  getCardName(cardId: number) {
      return this.cards().find(c => c.id === cardId)?.name || '未知卡片';
  }

  showDialog() {
      this.newRoute = { methodName: '', cardId: null };
      this.displayDialog = true;
  }

  saveRoute() {
      this.accountingService.createPaymentRoute(this.newRoute).subscribe({
          next: () => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '路由規則已建立' });
              this.displayDialog = false;
              this.loadData();
          }
      });
  }

  deleteRoute(id: number) {
      if (confirm('確定要刪除此路由規則嗎？')) {
          this.accountingService.deletePaymentRoute(id).subscribe(() => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '規則已刪除' });
              this.loadData();
          });
      }
  }
}
