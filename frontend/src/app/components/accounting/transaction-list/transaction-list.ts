import { Component, OnInit, inject, signal, ViewChild, computed, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AccountingService } from '../../../services/accounting.service';
import { Transaction, Category, CreditCard, PaymentMethod } from '../../../models/accounting.model';
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
import { RadioButtonModule } from 'primeng/radiobutton';
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
    MenuModule,
    RadioButtonModule
  ],
  providers: [MessageService],
  templateUrl: './transaction-list.html',
  styleUrl: './transaction-list.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TransactionListComponent implements OnInit {
  private accountingService = inject(AccountingService);
  private messageService = inject(MessageService);

  @ViewChild('menu') menu!: Menu;
  menuItems: MenuItem[] = [];

  transactions = signal<Transaction[]>([]);
  categories = signal<Category[]>([]);
  cards = signal<CreditCard[]>([]);
  paymentMethods = signal<PaymentMethod[]>([]);
  
  // Filter Signals
  selectedCategory = signal<string | undefined>(undefined);
  selectedPaymentMethod = signal<string | undefined>(undefined);
  selectedKeyword = signal<string>('');
  selectedType = signal<'ALL' | 'EXPENSE' | 'INCOME'>('ALL');
  selectedMonth = signal<Date>(new Date());

  monthTransactions = computed(() => {
    const current = this.selectedMonth();
    const year = current.getFullYear();
    const month = current.getMonth();
    return this.transactions().filter(txn => {
      const txnDate = new Date(txn.date);
      return txnDate.getFullYear() === year && txnDate.getMonth() === month;
    });
  });

  monthSummary = computed(() => {
    const txns = this.monthTransactions();
    const expense = txns
      .filter(t => t.transactionType === 'EXPENSE')
      .reduce((sum, t) => sum + (t.paidAmount || 0), 0);
    const income = txns
      .filter(t => t.transactionType === 'INCOME')
      .reduce((sum, t) => sum + (t.paidAmount || 0), 0);
    return {
      expense,
      income,
      net: income - expense,
      count: txns.length
    };
  });

  activeFilterTags = computed(() => {
    const tags: string[] = [];
    const cat = this.selectedCategory();
    const pm = this.selectedPaymentMethod();
    const keyword = this.selectedKeyword().trim();
    const type = this.selectedType();

    if (cat) tags.push(`分類：${cat}`);
    if (pm) tags.push(`支付：${pm}`);
    if (type !== 'ALL') tags.push(`類型：${type === 'EXPENSE' ? '支出' : '收入'}`);
    if (keyword) tags.push(`關鍵字：${keyword}`);
    return tags;
  });

  hasActiveFilters = computed(() => this.activeFilterTags().length > 0);

  filteredTransactions = computed(() => {
    let result = this.monthTransactions();
    const cat = this.selectedCategory();
    const pmValue = this.selectedPaymentMethod();
    const keyword = this.selectedKeyword().trim().toLowerCase();
    const type = this.selectedType();

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

    if (type !== 'ALL') {
      result = result.filter(txn => txn.transactionType === type);
    }

    if (keyword) {
      result = result.filter(txn =>
        (txn.item || '').toLowerCase().includes(keyword) ||
        (txn.note || '').toLowerCase().includes(keyword)
      );
    }

    return result;
  });

  displayDialog = false;
  isEdit = false;
  isGeneratingRecurring = false;
  paidAmountOverridden = false;
  txnDate = new Date();
  newTxn: any = this.resetNewTxn();
  selectedPaymentValue: string | null = null;

  typeOptions = [
    { label: '支出', value: 'EXPENSE' },
    { label: '收入', value: 'INCOME' }
  ];

  paymentOptions = signal<any[]>([]);
  filterPaymentOptions = signal<any[]>([]);

  toolOptions = computed(() => 
    this.paymentMethods().map(m => ({ label: m.name, value: m.name }))
  );

  ngOnInit() {
    this.loadData();
  }

  getSelectedMonthLabel() {
    const month = this.selectedMonth();
    return `${month.getFullYear()}年${month.getMonth() + 1}月`;
  }

  goPrevMonth() {
    const current = this.selectedMonth();
    this.selectedMonth.set(new Date(current.getFullYear(), current.getMonth() - 1, 1));
  }

  goNextMonth() {
    const current = this.selectedMonth();
    this.selectedMonth.set(new Date(current.getFullYear(), current.getMonth() + 1, 1));
  }

  goCurrentMonth() {
    const now = new Date();
    this.selectedMonth.set(new Date(now.getFullYear(), now.getMonth(), 1));
  }

  clearFilters() {
    this.selectedCategory.set(undefined);
    this.selectedPaymentMethod.set(undefined);
    this.selectedType.set('ALL');
    this.selectedKeyword.set('');
  }

  isNewDay(index: number): boolean {
    if (index === 0) return true;
    const current = this.filteredTransactions()[index];
    const previous = this.filteredTransactions()[index - 1];
    return current.date !== previous.date;
  }

  loadData() {
    this.accountingService.getTransactions().subscribe(data => {
        const sorted = data.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
        this.transactions.set(sorted);
    });
    this.accountingService.getCategories().subscribe(data => this.categories.set(data));
    
    forkJoin({
        cards: this.accountingService.getCards(),
        methods: this.accountingService.getPaymentMethods()
    }).subscribe(({ cards, methods }) => {
        this.cards.set(cards);
        this.paymentMethods.set(methods);
        
        // 1. 建立「整合型支付選單」: 現金 + 所有的信用卡
        const combined = [
            { label: '現金', value: 'CASH', type: 'CASH' },
            ...cards.map(c => ({ 
                label: `💳 ${c.name}`, 
                value: `CARD_${c.id}`, 
                type: 'CARD',
                cardId: c.id,
                defaultTool: c.defaultPaymentMethod || 'Apple Pay'
            }))
        ];
        this.paymentOptions.set(combined);

        // 2. 篩選器選項：保持原樣
        const filterOptions = [
            { label: '現金', value: '現金' },
            { label: '--- 信用卡 ---', value: null, disabled: true },
            ...cards.map(c => ({ label: `💳 ${c.name}`, value: c.id.toString() }))
        ];
        this.filterPaymentOptions.set(filterOptions);
    });
  }

  resetNewTxn() {
    this.selectedPaymentValue = 'CASH';
    this.paidAmountOverridden = false;
    return {
      item: '',
      date: '',
      category: '',
      categoryId: null,
      paidAmount: 0,
      transactionAmount: 0,
      paymentMethod: '現金',
      cardId: null,
      transactionType: 'EXPENSE',
      note: ''
    };
  }

  showDialog() {
    this.newTxn = this.resetNewTxn();
    this.selectedPaymentValue = 'CASH';
    this.paidAmountOverridden = false;
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
              visible: txn.transactionType === 'EXPENSE',
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
      this.paidAmountOverridden = txn.transactionAmount !== txn.paidAmount;
      this.txnDate = new Date(txn.date);
      this.selectedPaymentValue = txn.cardId ? `CARD_${txn.cardId}` : 'CASH';
      this.displayDialog = true;
  }

  onTransactionAmountChange(value: number | null | undefined) {
      const amount = value ?? 0;
      this.newTxn.transactionAmount = amount;
      if (!this.paidAmountOverridden) {
          this.newTxn.paidAmount = amount;
      }
  }

  onPaidAmountChange(value: number | null | undefined) {
      this.newTxn.paidAmount = value ?? 0;
      this.paidAmountOverridden = true;
  }

  onCategoryChange(id: number) {
      const cat = this.categories().find(c => c.id === id);
      if (cat) {
          this.newTxn.category = cat.name;
      }
  }

  onCombinedPaymentChange(event: any) {
      const selected = this.paymentOptions().find(o => o.value === event.value);
      if (!selected) return;

      if (selected.type === 'CASH') {
          this.newTxn.paymentMethod = '現金';
          this.newTxn.cardId = null;
      } else if (selected.type === 'CARD') {
          this.newTxn.cardId = selected.cardId;
          this.newTxn.paymentMethod = selected.defaultTool;
      }
      
      // 若使用者尚未手動覆寫，維持交易金額與實付金額同步
      if (!this.paidAmountOverridden) {
          this.newTxn.paidAmount = this.newTxn.transactionAmount;
      }
  }

  onRefund(txn: Transaction) {
      const amount = prompt(`請輸入退款/沖銷金額 (原始金額: ${txn.transactionAmount})`, txn.transactionAmount.toString());
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

  getCategoryTagStyle(name: string) {
      const hex = this.getCategoryColor(name);
      const rgb = this.hexToRgb(hex);
      if (!rgb) {
          return {
              'background-color': 'rgba(100, 116, 139, 0.16)',
              'border': '1px solid rgba(100, 116, 139, 0.38)',
              'color': '#334155'
          };
      }
      return {
          'background-color': `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.16)`,
          'border': `1px solid rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.42)`,
          'color': `rgb(${Math.max(40, Math.round(rgb.r * 0.65))}, ${Math.max(40, Math.round(rgb.g * 0.65))}, ${Math.max(40, Math.round(rgb.b * 0.65))})`
      };
  }

  private hexToRgb(hex: string) {
      const normalized = hex?.replace('#', '').trim();
      if (!normalized || !/^[0-9a-fA-F]{6}$/.test(normalized)) return null;
      const r = parseInt(normalized.substring(0, 2), 16);
      const g = parseInt(normalized.substring(2, 4), 16);
      const b = parseInt(normalized.substring(4, 6), 16);
      return { r, g, b };
  }

  saveTransaction() {
    const year = this.txnDate.getFullYear();
    const month = (this.txnDate.getMonth() + 1).toString().padStart(2, '0');
    const day = this.txnDate.getDate().toString().padStart(2, '0');
    const dateStr = `${year}-${month}-${day}`;
    
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
      if (this.isGeneratingRecurring) return;
      const now = new Date();
      const yearMonth = `${now.getFullYear()}年${now.getMonth() + 1}月`;
      const confirmed = confirm(`確定要同步 ${yearMonth} 的固定支出、訂閱與分期扣款嗎？`);
      if (!confirmed) return;

      this.isGeneratingRecurring = true;
      this.accountingService.triggerRecurringGeneration().subscribe({
          next: () => {
              this.messageService.add({ severity: 'success', summary: '同步完成', detail: `已同步 ${yearMonth} 定期交易` });
              this.loadData();
          },
          error: () => this.messageService.add({ severity: 'error', summary: '錯誤', detail: '同步失敗，請稍後再試' }),
          complete: () => { this.isGeneratingRecurring = false; }
      });
  }
}
