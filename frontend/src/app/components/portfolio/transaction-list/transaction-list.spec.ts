import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { describe, expect, it, vi } from 'vitest';

import { Transaction, TransactionType } from '../../../models/portfolio.model';
import { PortfolioService } from '../../../services/portfolio.service';
import { PortfolioTransactionListComponent } from './transaction-list';

describe('PortfolioTransactionListComponent', () => {
  it('displays the recorded trade price instead of an all-in unit price', async () => {
    const transaction: Transaction = {
      id: 56,
      symbol: '00919',
      name: '群益台灣精選高息',
      type: TransactionType.BUY,
      quantity: 67,
      price: 29.77,
      trade_date: '2026-07-15T00:00:00+08:00',
      fee: 1,
      tax: 0,
    };
    const portfolioService = {
      getSymbolNames: vi.fn().mockReturnValue(of({})),
      getTransactions: vi.fn().mockReturnValue(of({ items: [transaction], total: 1 })),
    };

    await TestBed.configureTestingModule({
      imports: [PortfolioTransactionListComponent],
      providers: [{ provide: PortfolioService, useValue: portfolioService }],
    }).compileComponents();

    const fixture = TestBed.createComponent(PortfolioTransactionListComponent);
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('67 股 @ 29.77');
    expect(text).not.toContain('67 股 @ 29.78');
    expect(fixture.componentInstance.allInTotal(transaction)).toBeCloseTo(1995.59);
  });
});
