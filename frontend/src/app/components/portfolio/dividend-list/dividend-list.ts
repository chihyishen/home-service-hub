import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PortfolioService } from '../../../services/portfolio.service';
import { Dividend } from '../../../models/portfolio.model';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { FormsModule } from '@angular/forms';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { DatePickerModule } from 'primeng/datepicker';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ToastModule } from 'primeng/toast';

@Component({
  selector: 'app-portfolio-dividends',
  standalone: true,
  imports: [CommonModule, TableModule, ButtonModule, DialogModule, FormsModule, InputTextModule, InputNumberModule, DatePickerModule, ConfirmDialogModule, ToastModule],
  providers: [ConfirmationService, MessageService],
  templateUrl: './dividend-list.html'
})
export class PortfolioDividendListComponent implements OnInit {
  private portfolioService = inject(PortfolioService);
  private confirmationService = inject(ConfirmationService);
  private messageService = inject(MessageService);

  dividends = signal<Dividend[]>([]);
  showDialog = signal<boolean>(false);
  isEdit = signal<boolean>(false);
  
  newDividend: Partial<Dividend> = {
    amount: 0
  };

  ngOnInit() {
    this.loadDividends();
  }

  loadDividends() {
    this.portfolioService.getDividends().subscribe(data => {
      this.dividends.set(data);
    });
  }

  openNew() {
    this.isEdit.set(false);
    this.newDividend = { amount: 0 };
    this.showDialog.set(true);
  }

  editDividend(dividend: Dividend) {
    this.isEdit.set(true);
    this.newDividend = { ...dividend, ex_dividend_date: dividend.ex_dividend_date ? new Date(dividend.ex_dividend_date) : undefined };
    this.showDialog.set(true);
  }

  deleteDividend(dividend: Dividend) {
    this.confirmationService.confirm({
      message: `確定要刪除 ${dividend.symbol} 的這筆股利紀錄嗎？`,
      header: '確認刪除',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        this.portfolioService.deleteDividend(dividend.id).subscribe(() => {
          this.messageService.add({ severity: 'success', summary: '成功', detail: '紀錄已刪除' });
          this.loadDividends();
        });
      }
    });
  }

  saveDividend() {
    if (this.isEdit() && this.newDividend.id) {
      this.portfolioService.updateDividend(this.newDividend.id, this.newDividend).subscribe(() => {
        this.showDialog.set(false);
        this.loadDividends();
        this.messageService.add({ severity: 'success', summary: '成功', detail: '紀錄已更新' });
      });
    } else {
      this.portfolioService.createDividend(this.newDividend).subscribe(() => {
        this.showDialog.set(false);
        this.loadDividends();
        this.messageService.add({ severity: 'success', summary: '成功', detail: '紀錄已新增' });
      });
    }
  }
}
