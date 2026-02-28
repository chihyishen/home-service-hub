import { Routes } from '@angular/router';
import { ItemListComponent } from './components/item-list/item-list';
import { AccountingDashboardComponent } from './components/accounting/dashboard/dashboard';
import { TransactionListComponent } from './components/accounting/transaction-list/transaction-list';
import { CardListComponent } from './components/accounting/card-list/card-list';
import { CategoryListComponent } from './components/accounting/category-list/category-list';
import { RecurringListComponent } from './components/accounting/recurring-list/recurring-list';
import { ManagementCenterComponent } from './components/accounting/management-center/management-center';
import { PortfolioDashboardComponent } from './components/portfolio/dashboard/dashboard';
import { PortfolioTransactionListComponent } from './components/portfolio/transaction-list/transaction-list';
import { PortfolioDividendListComponent } from './components/portfolio/dividend-list/dividend-list';

export const routes: Routes = [
  { path: '', component: ItemListComponent },
  
  // Portfolio routes
  { path: 'portfolio', component: PortfolioDashboardComponent },
  { path: 'portfolio/transactions', component: PortfolioTransactionListComponent },
  { path: 'portfolio/dividends', component: PortfolioDividendListComponent },

  // Accounting routes
  { path: 'accounting/dashboard', component: AccountingDashboardComponent },
  { path: 'accounting/transactions', component: TransactionListComponent },
  { path: 'accounting/settings', component: ManagementCenterComponent },
  { path: 'accounting/cards', component: CardListComponent },
  { path: 'accounting/categories', component: CategoryListComponent },
  { path: 'accounting/recurring', component: RecurringListComponent },

  { path: '**', redirectTo: '' }
];