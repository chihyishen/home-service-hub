import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TabsModule } from 'primeng/tabs';
import { CardListComponent } from '../card-list/card-list';
import { CategoryListComponent } from '../category-list/category-list';
import { RecurringListComponent } from '../recurring-list/recurring-list';
import { PaymentMethodListComponent } from '../payment-method-list/payment-method-list';

@Component({
  selector: 'app-management-center',
  standalone: true,
  imports: [
    CommonModule,
    TabsModule,
    CardListComponent,
    CategoryListComponent,
    RecurringListComponent,
    PaymentMethodListComponent
  ],
  templateUrl: './management-center.html',
  styleUrl: './management-center.scss'
})
export class ManagementCenterComponent {}
