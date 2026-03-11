import { Component, signal, inject, OnDestroy, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TooltipModule } from 'primeng/tooltip';

// 引入主要組件以實現不切頁切換
import { ItemListComponent } from './components/item-list/item-list';
import { ShoppingListComponent } from './components/shopping-list/shopping-list';
import { PortfolioDashboardComponent } from './components/portfolio/dashboard/dashboard';
import { PortfolioTransactionListComponent } from './components/portfolio/transaction-list/transaction-list';
import { PortfolioDividendListComponent } from './components/portfolio/dividend-list/dividend-list';
import { AccountingDashboardComponent } from './components/accounting/dashboard/dashboard';
import { TransactionListComponent } from './components/accounting/transaction-list/transaction-list';
import { ManagementCenterComponent } from './components/accounting/management-center/management-center';

type AppTab = 'inventory' | 'shopping' | 'portfolio' | 'portfolio-transactions' | 'portfolio-dividends' | 'acc-dashboard' | 'acc-transactions' | 'settings';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule, TooltipModule,
    ItemListComponent, ShoppingListComponent, PortfolioDashboardComponent, 
    PortfolioTransactionListComponent, PortfolioDividendListComponent,
    AccountingDashboardComponent, TransactionListComponent, ManagementCenterComponent
  ],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnDestroy {
  private themeMediaQuery?: MediaQueryList;
  private themeListener?: (event: MediaQueryListEvent) => void;
  
  protected readonly title = signal('交易紀錄');
  protected readonly isSidebarOpen = signal(false);
  
  // 當前選中的精確分頁
  protected readonly activeTab = signal<AppTab>('acc-transactions');

  // 計算當前屬於哪個大類別
  protected readonly mainTab = computed(() => {
    const tab = this.activeTab();
    if (tab === 'inventory' || tab === 'shopping') return 'supplies';
    if (tab.startsWith('portfolio')) return 'portfolio';
    if (tab.startsWith('acc-') || tab === 'settings') return 'accounting';
    return tab;
  });

  constructor() {
    this.initTheme();
    this.updateTitleByTab('acc-transactions');
  }

  protected setTab(tab: AppTab) {
    this.activeTab.set(tab);
    this.updateTitleByTab(tab);
    this.closeSidebar();
  }

  private updateTitleByTab(tab: AppTab) {
    const titles: Record<AppTab, string> = {
      'inventory': '庫存管理',
      'shopping': '採買清單',
      'portfolio': '投資概覽',
      'portfolio-transactions': '股票交易紀錄',
      'portfolio-dividends': '股利領取紀錄',
      'acc-dashboard': '記帳分析',
      'acc-transactions': '交易紀錄',
      'settings': '會計設定'
    };
    this.title.set(titles[tab] || '家庭服務中心');
  }

  ngOnDestroy() {
    if (!this.themeMediaQuery || !this.themeListener) return;
    if (this.themeMediaQuery.removeEventListener) {
      this.themeMediaQuery.removeEventListener('change', this.themeListener);
    } else {
      this.themeMediaQuery.removeListener(this.themeListener);
    }
  }

  protected toggleSidebar() {
    this.isSidebarOpen.update(v => !v);
  }

  protected closeSidebar() {
    this.isSidebarOpen.set(false);
  }

  private applyTheme(isDark: boolean) {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('app-dark-mode', isDark);
      document.documentElement.classList.toggle('app-light-mode', !isDark);
    }
  }

  private initTheme() {
    if (typeof window === 'undefined') return;

    this.themeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    this.applyTheme(this.themeMediaQuery.matches);

    this.themeListener = (event: MediaQueryListEvent) => {
      this.applyTheme(event.matches);
    };

    if (this.themeMediaQuery.addEventListener) {
      this.themeMediaQuery.addEventListener('change', this.themeListener);
    } else {
      this.themeMediaQuery.addListener(this.themeListener);
    }
  }
}
