import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PortfolioService } from '../../../services/portfolio.service';
import { Transaction, TransactionType } from '../../../models/portfolio.model';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { FormsModule } from '@angular/forms';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { SelectButtonModule } from 'primeng/selectbutton';
import { DatePickerModule } from 'primeng/datepicker';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ToastModule } from 'primeng/toast';

@Component({
  selector: 'app-portfolio-transactions',
  standalone: true,
  imports: [CommonModule, TableModule, ButtonModule, DialogModule, FormsModule, InputTextModule, InputNumberModule, SelectButtonModule, DatePickerModule, ConfirmDialogModule, ToastModule],
  providers: [ConfirmationService, MessageService],
  templateUrl: './transaction-list.html',
  styleUrl: './transaction-list.scss'
})
export class PortfolioTransactionListComponent implements OnInit {
  private portfolioService = inject(PortfolioService);
  private confirmationService = inject(ConfirmationService);
  private messageService = inject(MessageService);

  transactions = signal<Transaction[]>([]);
  showDialog = signal<boolean>(false);
  isEdit = signal<boolean>(false);
  
  newTransaction: Partial<Transaction> = {
    type: TransactionType.BUY,
    quantity: 0,
    price: 0,
    fee: 0,
    tax: 0
  };

  transactionTypes = [
    { label: '買進', value: TransactionType.BUY },
    { label: '賣出', value: TransactionType.SELL }
  ];

  ngOnInit() {
    this.loadTransactions();
  }

  loadTransactions() {
    this.portfolioService.getTransactions().subscribe(data => {
      this.transactions.set(data);
    });
  }

  openNew() {
    this.isEdit.set(false);
    this.newTransaction = { type: TransactionType.BUY, quantity: 0, price: 0, fee: 0, tax: 0 };
    this.showDialog.set(true);
  }

  editTransaction(transaction: Transaction) {
    this.isEdit.set(true);
    this.newTransaction = { ...transaction, trade_date: transaction.trade_date ? new Date(transaction.trade_date) : undefined };
    this.showDialog.set(true);
  }

  deleteTransaction(transaction: Transaction) {
    this.confirmationService.confirm({
      message: `確定要刪除 ${transaction.symbol} 的這筆交易紀錄嗎？`,
      header: '確認刪除',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        this.portfolioService.deleteTransaction(transaction.id).subscribe(() => {
          this.messageService.add({ severity: 'success', summary: '成功', detail: '紀錄已刪除' });
          this.loadTransactions();
        });
      }
    });
  }

  saveTransaction() {
    if (this.isEdit() && this.newTransaction.id) {
      this.portfolioService.updateTransaction(this.newTransaction.id, this.newTransaction).subscribe(() => {
        this.showDialog.set(false);
        this.loadTransactions();
        this.messageService.add({ severity: 'success', summary: '成功', detail: '紀錄已更新' });
      });
    } else {
      this.portfolioService.createTransaction(this.newTransaction).subscribe(() => {
        this.showDialog.set(false);
        this.loadTransactions();
        this.messageService.add({ severity: 'success', summary: '成功', detail: '紀錄已新增' });
      });
    }
  }
}
