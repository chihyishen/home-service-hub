import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AccountingService } from '../../../services/accounting.service';
import { MonthlyReport, CardUsageSummary, MonthlyCompareReport, CategoryDeltaSummary } from '../../../models/accounting.model';
import { ChartModule } from 'primeng/chart';
import { DatePickerModule } from 'primeng/datepicker';
import { ProgressBarModule } from 'primeng/progressbar';
import { FormsModule } from '@angular/forms';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';

@Component({
  selector: 'app-accounting-dashboard',
  standalone: true,
  imports: [CommonModule, ChartModule, DatePickerModule, FormsModule, CardModule, ProgressBarModule, ButtonModule, TableModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class AccountingDashboardComponent implements OnInit {
  private accountingService = inject(AccountingService);

  selectedMonth = new Date();
  report = signal<MonthlyReport | null>(null);
  compareReport = signal<MonthlyCompareReport | null>(null);
  cardUsage = signal<CardUsageSummary[]>([]);
  cardSortBy = signal<'usage' | 'name'>('usage');
  cardUsageView = signal<'cards' | 'table'>('cards');
  
  chartData: any;
  paymentChartData: any;
  chartOptions = {
    plugins: {
        legend: {
            position: 'bottom'
        }
    }
  };

  ngOnInit() {
    this.loadReport();
    this.loadCardUsage();
  }

  loadCardUsage() {
      this.accountingService.getCardUsage().subscribe(data => {
          this.sortAndSetCardUsage(data);
      });
  }

  toggleCardSort() {
      const current = this.cardSortBy();
      this.cardSortBy.set(current === 'usage' ? 'name' : 'usage');
      this.sortAndSetCardUsage(this.cardUsage());
  }

  private sortAndSetCardUsage(data: CardUsageSummary[]) {
    const sortedData = [...data].sort((a, b) => {
        if (this.cardSortBy() === 'usage') {
            if (b.usagePercentage !== a.usagePercentage) {
                return b.usagePercentage - a.usagePercentage;
            }
            return a.cardName.localeCompare(b.cardName);
        } else {
            return a.cardName.localeCompare(b.cardName);
        }
    });
    this.cardUsage.set(sortedData);
  }

  getProgressBarColor(percentage: number): string {
      if (percentage >= 100) return '#EF5350'; // Red
      if (percentage >= 80) return '#FFA726'; // Orange
      return '#66BB6A'; // Green
  }

  loadReport() {
    const year = this.selectedMonth.getFullYear();
    const month = this.selectedMonth.getMonth() + 1;

    this.accountingService.getMonthlyReport(year, month).subscribe(data => {
      this.report.set(data);
      this.prepareChartData(data);
      this.preparePaymentChartData(data);
    });

    this.accountingService.getMonthlyCompareReport(year, month).subscribe(data => {
      this.compareReport.set(data);
    });
  }

  getTopCategoryChanges(): CategoryDeltaSummary[] {
    const items = this.compareReport()?.categories ?? [];
    return items.filter(i => i.status !== 'flat').slice(0, 6);
  }

  getDeltaSign(delta: number): string {
    if (delta > 0) return '+';
    if (delta < 0) return '-';
    return '';
  }

  prepareChartData(report: MonthlyReport) {
    if (!report || !report.expenseBreakdown || report.expenseBreakdown.length === 0) {
        this.chartData = null;
        return;
    }

    const labels = report.expenseBreakdown.map(item => item.category);
    const data = report.expenseBreakdown.map(item => item.amount);

    this.chartData = {
      labels: labels,
      datasets: [
        {
          data: data,
          backgroundColor: [
            '#42A5F5', '#66BB6A', '#FFA726', '#AB47BC', '#EF5350', '#26A69A', '#EC407A', '#78909C'
          ]
        }
      ]
    };
  }

  preparePaymentChartData(report: MonthlyReport) {
    if (!report || !report.paymentBreakdown || report.paymentBreakdown.length === 0) {
        this.paymentChartData = null;
        return;
    }

    const labels = report.paymentBreakdown.map(item => item.method);
    const data = report.paymentBreakdown.map(item => item.amount);

    this.paymentChartData = {
      labels: labels,
      datasets: [
        {
          data: data,
          backgroundColor: [
            '#36A2EB', '#FF6384', '#FFCE56', '#4BC0C0', '#9966FF', '#C9CBCF'
          ]
        }
      ]
    };
  }
}
