import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { 
  Transaction, TransactionCreate, Category, CreditCard, 
  Subscription, Installment, MonthlyReport, PaymentMethod,
  CardUsageSummary
} from '../models/accounting.model';

@Injectable({
  providedIn: 'root'
})
export class AccountingService {
  private http = inject(HttpClient);
  private apiUrl = '/api/accounting';

  // Transactions
  getTransactions(skip = 0, limit = 100, category?: string): Observable<Transaction[]> {
    let url = `${this.apiUrl}/transactions/?skip=${skip}&limit=${limit}`;
    if (category) url += `&category=${category}`;
    return this.http.get<Transaction[]>(url);
  }

  getTransaction(id: number): Observable<Transaction> {
    return this.http.get<Transaction>(`${this.apiUrl}/transactions/${id}`);
  }

  createTransaction(data: TransactionCreate): Observable<Transaction> {
    return this.http.post<Transaction>(`${this.apiUrl}/transactions/`, data);
  }

  updateTransaction(id: number, data: Partial<TransactionCreate>): Observable<Transaction> {
    return this.http.put<Transaction>(`${this.apiUrl}/transactions/${id}`, data);
  }

  deleteTransaction(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/transactions/${id}`);
  }

  refundTransaction(id: number, amount: number): Observable<Transaction> {
    return this.http.post<Transaction>(`${this.apiUrl}/transactions/${id}/refund?refund_amount=${amount}`, {});
  }

  getMonthlyReport(year: number, month: number): Observable<MonthlyReport> {
    return this.http.get<MonthlyReport>(`${this.apiUrl}/transactions/report/${year}/${month}`);
  }

  // Cards
  getCards(): Observable<CreditCard[]> {
    return this.http.get<CreditCard[]>(`${this.apiUrl}/cards/`);
  }

  getCardUsage(): Observable<CardUsageSummary[]> {
    return this.http.get<CardUsageSummary[]>(`${this.apiUrl}/cards/usage`);
  }

  createCard(data: any): Observable<CreditCard> {
    return this.http.post<CreditCard>(`${this.apiUrl}/cards/`, data);
  }

  updateCard(id: number, data: any): Observable<CreditCard> {
    return this.http.put<CreditCard>(`${this.apiUrl}/cards/${id}`, data);
  }

  deleteCard(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/cards/${id}`);
  }

  // Categories
  getCategories(): Observable<Category[]> {
    return this.http.get<Category[]>(`${this.apiUrl}/categories/`);
  }

  createCategory(data: { name: string, color: string }): Observable<Category> {
    return this.http.post<Category>(`${this.apiUrl}/categories/`, data);
  }

  updateCategory(id: number, data: Partial<Category>): Observable<Category> {
    return this.http.put<Category>(`${this.apiUrl}/categories/${id}`, data);
  }

  deleteCategory(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/categories/${id}`);
  }

  // Payment Methods
  getPaymentMethods(): Observable<PaymentMethod[]> {
    return this.http.get<PaymentMethod[]>(`${this.apiUrl}/payment-methods/`);
  }

  createPaymentMethod(data: { name: string }): Observable<PaymentMethod> {
    return this.http.post<PaymentMethod>(`${this.apiUrl}/payment-methods/`, data);
  }

  updatePaymentMethod(id: number, data: Partial<PaymentMethod>): Observable<PaymentMethod> {
    return this.http.put<PaymentMethod>(`${this.apiUrl}/payment-methods/${id}`, data);
  }

  deletePaymentMethod(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/payment-methods/${id}`);
  }

  // Recurring
  getSubscriptions(): Observable<Subscription[]> {
    return this.http.get<Subscription[]>(`${this.apiUrl}/recurring/subscriptions`);
  }

  createSubscription(data: any): Observable<Subscription> {
    return this.http.post<Subscription>(`${this.apiUrl}/recurring/subscriptions`, data);
  }

  updateSubscription(id: number, data: any): Observable<Subscription> {
    return this.http.put<Subscription>(`${this.apiUrl}/recurring/subscriptions/${id}`, data);
  }

  toggleSubscription(id: number): Observable<Subscription> {
    return this.http.patch<Subscription>(`${this.apiUrl}/recurring/subscriptions/${id}/toggle`, {});
  }

  deleteSubscription(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/recurring/subscriptions/${id}`);
  }

  getInstallments(): Observable<Installment[]> {
    return this.http.get<Installment[]>(`${this.apiUrl}/recurring/installments`);
  }

  createInstallment(data: any): Observable<Installment> {
    return this.http.post<Installment>(`${this.apiUrl}/recurring/installments`, data);
  }

  updateInstallment(id: number, data: any): Observable<Installment> {
    return this.http.put<Installment>(`${this.apiUrl}/recurring/installments/${id}`, data);
  }

  deleteInstallment(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/recurring/installments/${id}`);
  }

  triggerRecurringGeneration(): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/recurring/generate`, {});
  }
}
