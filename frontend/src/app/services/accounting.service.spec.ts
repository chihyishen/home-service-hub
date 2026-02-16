import { describe, it, expect, beforeEach } from 'vitest';
import { AccountingService } from './accounting.service';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

describe('AccountingService', () => {
  let service: AccountingService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AccountingService]
    });
    service = TestBed.inject(AccountingService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('應正確獲取月度報表', () => {
    const mockReport = {
      period: '2026-02',
      summary: {
        totalIncome: 10000,
        totalExpense: 5000,
        surplus: 5000,
        savingsRate: 50
      },
      expenseBreakdown: [
        { category: 'Food', amount: 3000, percentage: 60 },
        { category: 'Transport', amount: 2000, percentage: 40 }
      ],
      topExpenses: []
    };

    service.getMonthlyReport(2026, 2).subscribe(report => {
      expect(report.summary.totalIncome).toBe(10000);
      expect(report.expenseBreakdown.length).toBe(2);
      expect(report.expenseBreakdown[0].category).toBe('Food');
    });

    const req = httpMock.expectOne('/api/accounting/transactions/report/2026/2');
    expect(req.request.method).toBe('GET');
    req.flush(mockReport);
  });
});
