import { TestBed } from '@angular/core/testing';
import { EMPTY, throwError } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AccountingService } from '../../../services/accounting.service';
import { MessageService } from 'primeng/api';
import { TransactionListComponent } from './transaction-list';

describe('TransactionListComponent', () => {
  const triggerRecurringGeneration = vi.fn();
  let component: TransactionListComponent;

  beforeEach(() => {
    triggerRecurringGeneration.mockReset();
    TestBed.configureTestingModule({
      providers: [
        { provide: AccountingService, useValue: { triggerRecurringGeneration } },
        { provide: MessageService, useValue: { add: vi.fn() } },
      ],
    });
    vi.stubGlobal('confirm', () => true);
    component = TestBed.runInInjectionContext(() => new TransactionListComponent());
  });

  afterEach(() => vi.unstubAllGlobals());

  it('allows retrying recurring generation after a failed request', () => {
    triggerRecurringGeneration.mockReturnValueOnce(throwError(() => new Error('failed')));
    triggerRecurringGeneration.mockReturnValueOnce(EMPTY);

    component.generateRecurring();
    expect(component.isGeneratingRecurring).toBe(false);

    component.generateRecurring();

    expect(triggerRecurringGeneration).toHaveBeenCalledTimes(2);
    expect(component.isGeneratingRecurring).toBe(false);
  });
});
