import { Component, OnInit, inject, signal, ViewChild, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AccountingService } from '../../../services/accounting.service';
import { Subscription, Installment, Category, CreditCard, PaymentMethod } from '../../../models/accounting.model';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { TabsModule } from 'primeng/tabs';
import { TagModule } from 'primeng/tag';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { SelectModule } from 'primeng/select';
import { DatePickerModule } from 'primeng/datepicker';
import { ToastModule } from 'primeng/toast';
import { MenuModule } from 'primeng/menu';
import { MessageService, MenuItem } from 'primeng/api';
import { forkJoin } from 'rxjs';
import { Menu } from 'primeng/menu';

@Component({
  selector: 'app-recurring-list',
  standalone: true,
  imports: [
    CommonModule, 
    FormsModule, 
    TableModule, 
    ButtonModule, 
    TabsModule, 
    TagModule,
    DialogModule,
    InputTextModule,
    InputNumberModule,
    SelectModule,
    DatePickerModule,
    ToastModule,
    MenuModule
  ],
  providers: [MessageService],
  templateUrl: './recurring-list.html',
  styleUrl: './recurring-list.scss'
})
export class RecurringListComponent implements OnInit {
  private accountingService = inject(AccountingService);
  private messageService = inject(MessageService);

  @ViewChild('menu') menu!: Menu;
  menuItems: MenuItem[] = [];

  subscriptions = signal<Subscription[]>([]);
  fixedExpenses = computed(() => this.subscriptions().filter(s => s.subType === 'FIXED_EXPENSE'));
  digitalSubscriptions = computed(() => this.subscriptions().filter(s => s.subType === 'SUBSCRIPTION'));
  
  installments = signal<Installment[]>([]);
  categories = signal<Category[]>([]);
  cards = signal<CreditCard[]>([]);
  paymentOptions = signal<any[]>([]);

  displaySubDialog = false;
  displayInstDialog = false;
  isEditSub = false;
  isEditInst = false;

  newSub: any = this.resetSub();
  newInst: any = this.resetInst();
  instStartDate = new Date();

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    forkJoin({
        subs: this.accountingService.getSubscriptions(),
        insts: this.accountingService.getInstallments(),
        cats: this.accountingService.getCategories(),
        cards: this.accountingService.getCards(),
        methods: this.accountingService.getPaymentMethods()
    }).subscribe(({ subs, insts, cats, cards, methods }) => {
        this.subscriptions.set(subs);
        this.installments.set(insts);
        this.categories.set(cats);
        this.cards.set(cards);
        
        const options = [
            ...methods.map(m => ({ label: m.name, value: m.name })),
            { label: '信用卡', value: '信用卡' } // 確保有預設值
        ];
        // 去重
        const uniqueOptions = Array.from(new Map(options.map(item => [item.value, item])).values());
        this.paymentOptions.set(uniqueOptions);
    });
  }

  resetSub(type: 'FIXED_EXPENSE' | 'SUBSCRIPTION' = 'SUBSCRIPTION') {
      return { 
          name: '', 
          amount: 0, 
          category: '', 
          categoryId: null, 
          subType: type, 
          dayOfMonth: 1, 
          paymentMethod: '信用卡' 
      };
  }

  showSubMenu(event: MouseEvent, sub: Subscription) {
      this.menuItems = [
          { label: '編輯', icon: 'pi pi-pencil', command: () => this.editSub(sub) },
          { separator: true },
          { label: '刪除', icon: 'pi pi-trash', styleClass: 'text-danger', command: () => this.deleteSub(sub.id) }
      ];
      this.menu.toggle(event);
  }

  showInstMenu(event: MouseEvent, inst: Installment) {
      this.menuItems = [
          { label: '編輯', icon: 'pi pi-pencil', command: () => this.editInst(inst) },
          { separator: true },
          { label: '刪除', icon: 'pi pi-trash', styleClass: 'text-danger', command: () => this.deleteInst(inst.id) }
      ];
      this.menu.toggle(event);
  }

  resetInst() {
      return {
          name: '',
          totalAmount: 0,
          monthlyAmount: 0,
          totalPeriods: 12,
          remainingPeriods: 12,
          startDate: new Date().toISOString().split('T')[0],
          cardId: null,
          paymentMethod: '信用卡'
      };
  }

  showSubDialog(type: 'FIXED_EXPENSE' | 'SUBSCRIPTION' = 'SUBSCRIPTION') {
      this.newSub = this.resetSub(type);
      this.isEditSub = false;
      this.displaySubDialog = true;
  }

  editSub(sub: Subscription) {
      this.isEditSub = true;
      this.newSub = { ...sub, paymentMethod: sub.paymentMethod || '信用卡' };
      this.displaySubDialog = true;
  }

  onSubCategoryChange(id: number) {
      const cat = this.categories().find(c => c.id === id);
      if (cat) {
          this.newSub.category = cat.name;
      }
  }

  showInstDialog() {
      this.newInst = this.resetInst();
      this.instStartDate = new Date();
      this.isEditInst = false;
      this.displayInstDialog = true;
  }

  editInst(inst: Installment) {
      this.isEditInst = true;
      this.newInst = { ...inst };
      this.instStartDate = new Date(inst.startDate);
      this.displayInstDialog = true;
  }

  calcMonthly() {
      if (this.newInst.totalAmount > 0 && this.newInst.totalPeriods > 0) {
          this.newInst.monthlyAmount = Math.round(this.newInst.totalAmount / this.newInst.totalPeriods);
          // 預設剩餘期數等於總期數，方便新計畫輸入；舊計畫則可手動再修改 remainingPeriods
          if (this.newInst.remainingPeriods === 0 || this.newInst.remainingPeriods > this.newInst.totalPeriods) {
              this.newInst.remainingPeriods = this.newInst.totalPeriods;
          }
      }
  }

  saveSub() {
      if (this.isEditSub) {
          this.accountingService.updateSubscription(this.newSub.id, this.newSub).subscribe({
              next: () => {
                  this.messageService.add({ severity: 'success', summary: '成功', detail: '項目已更新' });
                  this.displaySubDialog = false;
                  this.loadData();
              }
          });
      } else {
          this.accountingService.createSubscription(this.newSub).subscribe({
              next: () => {
                  this.messageService.add({ severity: 'success', summary: '成功', detail: '項目已建立' });
                  this.displaySubDialog = false;
                  this.loadData();
              }
          });
      }
  }

  saveInst() {
      const dateStr = this.instStartDate.toISOString().split('T')[0];
      this.newInst.startDate = dateStr;
      
      if (this.isEditInst) {
          this.accountingService.updateInstallment(this.newInst.id, this.newInst).subscribe({
              next: () => {
                  this.messageService.add({ severity: 'success', summary: '成功', detail: '分期計畫已更新' });
                  this.displayInstDialog = false;
                  this.loadData();
              }
          });
      } else {
          this.accountingService.createInstallment(this.newInst).subscribe({
              next: () => {
                  this.messageService.add({ severity: 'success', summary: '成功', detail: '分期計畫已建立' });
                  this.displayInstDialog = false;
                  this.loadData();
              }
          });
      }
  }

  toggleSub(id: number) {
      this.accountingService.toggleSubscription(id).subscribe(() => this.loadData());
  }

  deleteSub(id: number) {
      if (confirm('確定要刪除此訂閱項目嗎？')) {
          this.accountingService.deleteSubscription(id).subscribe(() => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '訂閱項目已刪除' });
              this.loadData();
          });
      }
  }

  deleteInst(id: number) {
      if (confirm('確定要刪除此分期計畫嗎？')) {
          this.accountingService.deleteInstallment(id).subscribe(() => {
              this.messageService.add({ severity: 'success', summary: '成功', detail: '分期計畫已刪除' });
              this.loadData();
          });
      }
  }
}
