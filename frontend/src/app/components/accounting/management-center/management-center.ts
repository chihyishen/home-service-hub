import { Component, signal, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { CardListComponent } from '../card-list/card-list';
import { CategoryListComponent } from '../category-list/category-list';
import { RecurringListComponent } from '../recurring-list/recurring-list';
import { PaymentMethodListComponent } from '../payment-method-list/payment-method-list';

type ManagementTab = 'cards' | 'payments' | 'categories' | 'recurring';

@Component({
  selector: 'app-management-center',
  imports: [
    CommonModule,
    ButtonModule,
    CardListComponent,
    CategoryListComponent,
    RecurringListComponent,
    PaymentMethodListComponent
  ],
  templateUrl: './management-center.html',
  styleUrl: './management-center.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManagementCenterComponent {
  activeTab = signal<ManagementTab>('cards');
  readonly sections: Array<{ value: ManagementTab; label: string; shortLabel: string; icon: string; desc: string }> = [
    { value: 'cards', label: '信用卡管理', shortLabel: '卡片', icon: 'pi-credit-card', desc: '管理結帳日、預警門檻與預設工具' },
    { value: 'payments', label: '支付方式', shortLabel: '支付', icon: 'pi-wallet', desc: '管理現金、轉帳與電子支付選項' },
    { value: 'categories', label: '支出分類', shortLabel: '分類', icon: 'pi-tags', desc: '統一分類名稱與色票策略' },
    { value: 'recurring', label: '定期與分期', shortLabel: '定期', icon: 'pi-refresh', desc: '管理固定扣款、訂閱與分期計畫' }
  ];
}
