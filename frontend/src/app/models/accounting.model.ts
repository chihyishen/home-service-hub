export type TransactionType = 'EXPENSE' | 'INCOME';

export interface Category {
  id: number;
  name: string;
  color: string;
}

export interface PaymentMethod {
  id: number;
  name: string;
  isActive: boolean;
}

export interface CreditCard {
  id: number;
  name: string;
  billingDay: number;
  rewardCycleType: string;
  alertThreshold: number;
  defaultPaymentMethod?: string;
}

export interface Transaction {
  id: number;
  date: string;
  category: string;
  item: string;
  paidAmount: number;
  transactionAmount: number;
  transactionType: TransactionType;
  paymentMethod: string;
  cardId?: number;
  cardName?: string;
  note?: string;
  relatedTransactionId?: number;
  createdAt?: string;
}

export interface TransactionCreate {
  date: string;
  category: string;
  item: string;
  paidAmount: number;
  transactionAmount: number;
  transactionType: TransactionType;
  paymentMethod: string;
  cardId?: number;
  note?: string;
}

export interface CategorySummary {
  category: string;
  amount: number;
  percentage: number;
}

export interface PaymentMethodSummary {
  method: string;
  amount: number;
}

export interface MonthlyReportSummary {
  totalIncome: number;
  totalExpense: number;
  surplus: number;
  savingsRate: number;
}

export interface CardUsageSummary {
  cardName: string;
  billingCycleStart: string;
  billingCycleEnd: string;
  currentUsage: number;
  alertThreshold: number;
  usagePercentage: number;
  remainingToThreshold: number;
  isNearLimit: boolean;
  isOverLimit: boolean;
}

export interface MonthlyReport {
  period: string;
  summary: MonthlyReportSummary;
  expenseBreakdown: CategorySummary[];
  paymentBreakdown: PaymentMethodSummary[];
  topExpenses: Transaction[];
}

export interface CategoryDeltaSummary {
  category: string;
  currentAmount: number;
  previousAmount: number;
  deltaAmount: number;
  deltaPercent: number;
  status: 'up' | 'down' | 'new' | 'gone' | 'flat';
}

export interface MonthlyCompareSummary {
  totalExpenseDelta: number;
  topIncreaseCategory?: string | null;
  topDecreaseCategory?: string | null;
}

export interface MonthlyCompareReport {
  period: string;
  baselinePeriod: string;
  categories: CategoryDeltaSummary[];
  summary: MonthlyCompareSummary;
}

export interface Subscription {
  id: number;
  name: string;
  amount: number;
  category: string;
  categoryId?: number;
  subType: 'FIXED_EXPENSE' | 'SUBSCRIPTION';
  paymentMethod?: string;
  dayOfMonth: number;
  cardId?: number;
  cardName?: string;
  active: boolean;
}

export interface Installment {
  id: number;
  name: string;
  totalAmount: number;
  monthlyAmount: number;
  paymentMethod?: string;
  totalPeriods: number;
  remainingPeriods: number;
  startDate: string;
  cardId?: number;
  cardName?: string;
}
