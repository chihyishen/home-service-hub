import { Component, signal, inject } from '@angular/core';
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
export class App {
  private router = inject(Router);
  protected readonly title = signal('家庭服務中心');

  constructor() {
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd)
    ).subscribe((event: any) => {
      this.updateTitle(event.urlAfterRedirects);
    });
  }

  private updateTitle(url: string) {
    if (url.includes('accounting/dashboard')) this.title.set('記帳分析');
    else if (url.includes('accounting/transactions')) this.title.set('交易紀錄');
    else if (url.includes('accounting/cards')) this.title.set('信用卡管理');
    else if (url.includes('accounting/categories')) this.title.set('分類維護');
    else if (url.includes('accounting/recurring')) this.title.set('訂閱項目管理');
    else if (url === '/') this.title.set('庫存管理');
    else this.title.set('家庭服務中心');
  }
}
