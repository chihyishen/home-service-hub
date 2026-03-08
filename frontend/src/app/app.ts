import { Component, signal, inject, OnDestroy } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnDestroy {
  private router = inject(Router);
  private themeMediaQuery?: MediaQueryList;
  private themeListener?: (event: MediaQueryListEvent) => void;
  
  protected readonly title = signal('家庭服務中心');
  protected readonly isSidebarOpen = signal(false);

  constructor() {
    this.initTheme();
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: any) => {
      this.updateTitle(event.urlAfterRedirects);
      this.closeSidebar(); // Close sidebar on navigation
    });
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

  private updateTitle(url: string) {
    if (url.includes('accounting/dashboard')) this.title.set('記帳分析');
    else if (url.includes('accounting/transactions')) this.title.set('交易紀錄');
    else if (url.includes('accounting/cards')) this.title.set('信用卡管理');
    else if (url.includes('accounting/categories')) this.title.set('分類維護');
    else if (url.includes('accounting/recurring')) this.title.set('訂閱項目管理');
    else if (url.includes('shopping-list')) this.title.set('採買清單');
    else if (url === '/') this.title.set('庫存管理');
    else this.title.set('家庭服務中心');
  }

  private initTheme() {
    if (typeof window === 'undefined') return;

    this.themeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Initial sync with system
    this.applyTheme(this.themeMediaQuery.matches);

    // Listen to system changes
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
