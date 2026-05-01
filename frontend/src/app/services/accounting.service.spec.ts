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

  it('應正確獲取年度報表', () => {
    const mockAnnualReport = {
      year: 2026,
      monthlyTrend: [
        { month: '2026-01', totalIncome: 50000, totalExpense: 32000, surplus: 18000 },
        { month: '2026-02', totalIncome: 48000, totalExpense: 30000, surplus: 18000 }
      ],
      categoryTrend: [
        {
          category: '餐飲',
          monthlyAmounts: [3200, 2800, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
          total: 6000,
          average: 500
        }
      ],
      summary: {
        totalIncome: 98000,
        totalExpense: 62000,
        surplus: 36000,
        savingsRate: 36.7,
        highestExpenseMonth: '2026-01',
        lowestExpenseMonth: '2026-02'
      }
    };

    service.getAnnualReport(2026).subscribe(report => {
      expect(report.year).toBe(2026);
      expect(report.monthlyTrend[0].totalExpense).toBe(32000);
      expect(report.categoryTrend[0].category).toBe('餐飲');
      expect(report.summary.highestExpenseMonth).toBe('2026-01');
    });

    const req = httpMock.expectOne('/api/accounting/transactions/report/annual/2026');
    expect(req.request.method).toBe('GET');
    req.flush(mockAnnualReport);
  });
});
