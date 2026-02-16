import { Component, OnInit, inject, signal, ViewChild, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AccountingService } from '../../../services/accounting.service';
import { Transaction, Category, CreditCard, PaymentMethod, PaymentRoute } from '../../../models/accounting.model';
import { forkJoin } from 'rxjs';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { DialogModule } from 'primeng/dialog';
import { DatePickerModule } from 'primeng/datepicker';
import { SelectModule } from 'primeng/select';
import { TagModule } from 'primeng/tag';
import { ToastModule } from 'primeng/toast';
import { TooltipModule } from 'primeng/tooltip';
import { MenuModule } from 'primeng/menu';
import { MessageService, MenuItem } from 'primeng/api';
import { Menu } from 'primeng/menu';

@Component({
  selector: 'app-transaction-list',
  standalone: true,
  imports: [
    CommonModule, 
    FormsModule, 
    TableModule, 
    ButtonModule, 
    InputTextModule, 
    InputNumberModule,
    DialogModule, 
    SelectModule,
    TagModule,
    DatePickerModule,
    ToastModule,
    TooltipModule,
    MenuModule
  ],
  providers: [MessageService],
  templateUrl: './transaction-list.html',
  styleUrl: './transaction-list.scss'
})
export class TransactionListComponent implements OnInit {
  private accountingService = inject(AccountingService);
  private messageService = inject(MessageService);

  @ViewChild('menu') menu!: Menu;
  menuItems: MenuItem[] = [];

  transactions = signal<Transaction[]>([]);
  categories = signal<Category[]>([]);
  cards = signal<CreditCard[]>([]);
  paymentRoutes = signal<PaymentRoute[]>([]);
  
  // Filter Signals
  selectedCategory = signal<string | undefined>(undefined);
  selectedPaymentMethod = signal<string | undefined>(undefined);

  filteredTransactions = computed(() => {
    let result = this.transactions();
    const cat = this.selectedCategory();
    const pmValue = this.selectedPaymentMethod();

    if (cat) {
      result = result.filter(txn => txn.category === cat);
    }
    
    if (pmValue) {
        // 篩選時同時比對 paymentMethod 文字或 cardId (若選的是卡片)
        const isCardId = !isNaN(Number(pmValue));
        if (isCardId) {
            const cardId = Number(pmValue);
            result = result.filter(txn => txn.cardId === cardId);
        } else {
            result = result.filter(txn => txn.paymentMethod === pmValue);
        }
    }

    return result;
  });

  displayDialog = false;
  isEdit = false;
  txnDate = new Date();
  newTxn: any = this.resetNewTxn();

  typeOptions = [
    { label: '支出', value: 'EXPENSE' },
    { label: '收入', value: 'INCOME' }
  ];

  paymentOptions = signal<any[]>([]);
  filterPaymentOptions = signal<any[]>([]);

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.accountingService.getTransactions().subscribe(data => {
        const sorted = data.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
        this.transactions.set(sorted);
    });
    this.accountingService.getCategories().subscribe(data => this.categories.set(data));
    
    forkJoin({
        cards: this.accountingService.getCards(),
        methods: this.accountingService.getPaymentMethods(),
        routes: this.accountingService.getPaymentRoutes()
    }).subscribe(({ cards, methods, routes }) => {
        this.cards.set(cards);
        this.paymentRoutes.set(routes);
        
        // 支付方式選項僅包含純支付工具
        const options = methods.map(m => ({ label: m.name, value: m.name }));
        if (!options.some(o => o.value === '現金')) {
            options.unshift({ label: '現金', value: '現金' });
        }
        this.paymentOptions.set(options);

        // 篩選器選項：包含支付工具與信用卡
        const filterOptions = [
            { label: '--- 支付工具 ---', value: null, disabled: true },
            ...options,
            { label: '--- 信用卡 ---', value: null, disabled: true },
            ...cards.map(c => ({ label: `💳 ${c.name}`, value: c.id.toString() }))
        ];
        this.filterPaymentOptions.set(filterOptions);
    });
  }

  resetNewTxn() {
    return {
      item: '',
      date: '',
      category: '',
      categoryId: null,
      personalAmount: 0,
      actualSwipe: 0,
      paymentMethod: '現金',
      cardId: null,
      transactionType: 'EXPENSE',
      note: ''
    };
  }

  showDialog() {
    this.newTxn = this.resetNewTxn();
    this.txnDate = new Date();
    this.isEdit = false;
    this.displayDialog = true;
  }

  showMenu(event: MouseEvent, txn: Transaction) {
      this.menuItems = [
          { 
              label: '編輯', 
              icon: 'pi pi-pencil', 
              command: () => this.editTransaction(txn) 
          },
          { 
              label: '申請退款/沖銷', 
              icon: 'pi pi-undo', 
              visible: txn.transactionType === 'EXPENSE' && txn.status === 'COMPLETED',
              command: () => this.onRefund(txn)
          },
          { separator: true },
          { 
              label: '刪除', 
              icon: 'pi pi-trash', 
              styleClass: 'text-danger', 
              command: () => this.deleteTransaction(txn.id) 
          }
      ];
      this.menu.toggle(event);
  }

  editTransaction(txn: Transaction) {
      this.isEdit = true;
      this.newTxn = { ...txn };
      this.txnDate = new Date(txn.date);
      this.displayDialog = true;
  }

  onCategoryChange(id: number) {
      const cat = this.categories().find(c => c.id === id);
      if (cat) {
          this.newTxn.category = cat.name;
      }
  }

  onPaymentMethodChange(val: string) {
      // 1. 檢查是否有自動路由規則
      const route = this.paymentRoutes().find(r => r.methodName === val);
      if (route) {
          this.newTxn.cardId = route.cardId;
      } else if (val === '現金') {
          this.newTxn.cardId = null;
      }
      
      // 2. 自動同步實際刷卡金額 (若尚未填寫)
      if (this.newTxn.cardId && (this.newTxn.actualSwipe === 0 || !this.isEdit)) {
          this.newTxn.actualSwipe = this.newTxn.personalAmount;
      }
  }

  getStatusSeverity(status: string): "success" | "warn" | "danger" | "secondary" | "info" | undefined {
      switch (status) {
          case 'COMPLETED': return 'success';
          case 'PENDING':
          case 'PENDING_SUB':
          case 'PENDING_INSTALLMENT': return 'warn';
          case 'CANCELLED': return 'danger';
          default: return 'info';
      }
  }

  getStatusLabel(status: string): string {
      switch (status) {
          case 'COMPLETED': return '已完成';
          case 'PENDING': return '待處理';
          case 'PENDING_SUB': return '訂閱中';
          case 'PENDING_INSTALLMENT': return '分期中';
          case 'CANCELLED': return '已取消';
          default: return status;
      }
  }

  onRefund(txn: Transaction) {
      const amount = prompt(`請輸入退款/沖銷金額 (原始金額: ${txn.personalAmount})`, txn.personalAmount.toString());
      if (amount && !isNaN(Number(amount))) {
          this.accountingService.refundTransaction(txn.id, Number(amount)).subscribe({
              next: () => {
                  this.messageService.add({ severity: 'success', summary: '成功', detail: '已建立沖銷交易' });
                  this.loadData();
              },
              error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '沖銷失敗' })
          });
      }
  }

  getCategoryColor(name: string) {
      const cat = this.categories().find(c => c.name === name);
      return cat ? cat.color : '#64748b'; // 使用更明亮的藍灰色作為預設
  }

  saveTransaction() {
    const dateStr = this.txnDate.toISOString().split('T')[0];
    this.newTxn.date = dateStr;

    if (this.isEdit) {
        this.accountingService.updateTransaction(this.newTxn.id, this.newTxn).subscribe({
            next: () => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '交易已更新' });
              this.displayDialog = false;
              this.loadData();
            },
            error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '更新失敗' })
          });
    } else {
        this.accountingService.createTransaction(this.newTxn).subscribe({
            next: () => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '交易已建立' });
              this.displayDialog = false;
              this.loadData();
            },
            error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '建立失敗' })
          });
    }
  }

  deleteTransaction(id: number) {
    if (confirm('確定要刪除此筆交易嗎？')) {
      this.accountingService.deleteTransaction(id).subscribe({
        next: () => {
          this.messageService.add({ severity: 'success', summary: '成功', detail: '交易已刪除' });
          this.loadData();
        },
        error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '刪除失敗' })
      });
    }
  }

  generateRecurring() {
      this.accountingService.triggerRecurringGeneration().subscribe({
          next: () => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '已觸發定期帳生成' });
              this.loadData();
          },
          error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '生成失敗' })
      });
  }
}
