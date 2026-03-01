import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PortfolioService } from '../../../services/portfolio.service';
import { PortfolioSummary, StockHolding } from '../../../models/portfolio.model';
import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ButtonModule } from 'primeng/button';
import { TooltipModule } from 'primeng/tooltip';

@Component({
  selector: 'app-portfolio-dashboard',
  standalone: true,
  imports: [CommonModule, CardModule, TableModule, TagModule, ButtonModule, TooltipModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class PortfolioDashboardComponent implements OnInit {
  private portfolioService = inject(PortfolioService);
  protected readonly Number = Number;

  summary = signal<PortfolioSummary | null>(null);
  loading = signal<boolean>(false);
  showWithDividend = signal<boolean>(false);

  ngOnInit() {
    this.loadSummary();
  }

  toggleDividend() {
    this.showWithDividend.set(!this.showWithDividend());
  }

  loadSummary() {
    this.loading.set(true);
    this.portfolioService.getSummary().subscribe({
      next: (data) => {
        this.summary.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load portfolio summary', err);
        this.loading.set(false);
      }
    });
  }

  getPnlColor(value: number | string): 'success' | 'secondary' | 'info' | 'warn' | 'danger' | 'contrast' {
    const num = Number(value);
    if (num > 0) return 'danger';
    if (num < 0) return 'success';
    return 'info';
  }

  formatCurrency(value: number | string): string {
    return new Intl.NumberFormat('zh-TW', { style: 'currency', currency: 'TWD', minimumFractionDigits: 0 }).format(Number(value));
  }
}
