import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  PortfolioSummary,
  Transaction,
  Dividend,
  ImportKind,
  ImportResult,
  NetworthPoint,
  RecalcStatus,
  RecalcTriggerResponse,
  UpcomingEvent,
  Paged,
  TransactionQuery,
  DividendQuery,
  RealizedPnlPaged,
  RealizedPnlQuery,
} from '../models/portfolio.model';

function buildParams(query: Record<string, unknown>): HttpParams {
  let params = new HttpParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === '') continue;
    params = params.set(key, String(value));
  }
  return params;
}

@Injectable({
  providedIn: 'root'
})
export class PortfolioService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiUrl}/portfolio`;
  private baseUrl = `${this.apiUrl}/transactions`;

  getSummary(): Observable<PortfolioSummary> {
    return this.http.get<PortfolioSummary>(`${this.apiUrl}/summary`);
  }

  refreshQuotes(): Observable<{
    refresh_scheduled: boolean;
    date: string;
    touched_symbols: string[];
  } | null> {
    return this.http.post<{
      refresh_scheduled: boolean;
      date: string;
      touched_symbols: string[];
    } | null>(`${this.apiUrl}/imports/refresh-quotes`, null);
  }

  getTransactions(query: TransactionQuery = {}): Observable<Paged<Transaction>> {
    return this.http.get<Paged<Transaction>>(`${this.apiUrl}/transactions`, {
      params: buildParams(query as Record<string, unknown>),
    });
  }

  createTransaction(transaction: Partial<Transaction>): Observable<Transaction> {
    return this.http.post<Transaction>(this.baseUrl, transaction);
  }

  updateTransaction(id: number, transaction: Partial<Transaction>): Observable<Transaction> {
    return this.http.put<Transaction>(`${this.baseUrl}/${id}`, transaction);
  }

  deleteTransaction(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/${id}`);
  }

  getDividends(query: DividendQuery = {}): Observable<Paged<Dividend>> {
    return this.http.get<Paged<Dividend>>(`${this.apiUrl}/dividends`, {
      params: buildParams(query as Record<string, unknown>),
    });
  }

  getRealizedPnl(query: RealizedPnlQuery = {}): Observable<RealizedPnlPaged> {
    return this.http.get<RealizedPnlPaged>(`${this.apiUrl}/realized-pnl`, {
      params: buildParams(query as Record<string, unknown>),
    });
  }

  createDividend(dividend: Partial<Dividend>): Observable<Dividend> {
    return this.http.post<Dividend>(`${this.apiUrl}/dividends`, dividend);
  }

  updateDividend(id: number, dividend: Partial<Dividend>): Observable<Dividend> {
    return this.http.put<Dividend>(`${this.apiUrl}/dividends/${id}`, dividend);
  }

  deleteDividend(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/dividends/${id}`);
  }

  verifyOverrideSymbol(
    name: string,
    code: string,
    tradeDate: string,
  ): Observable<{
    name: string;
    code: string;
    status: 'verified' | 'name_mismatch' | 'not_traded_on_date' | 'fetch_failed' | 'user_overridden';
    expected_name: string | null;
    fetched_name: string | null;
  }> {
    return this.http.post<{
      name: string;
      code: string;
      status:
        | 'verified'
        | 'name_mismatch'
        | 'not_traded_on_date'
        | 'fetch_failed'
        | 'user_overridden';
      expected_name: string | null;
      fetched_name: string | null;
    }>(`${this.apiUrl}/imports/verify-symbol`, {
      name,
      code,
      trade_date: tradeDate,
    });
  }

  uploadCsv(
    kind: ImportKind,
    file: File,
    dryRun: boolean,
    hasHeader: boolean = true,
    nameOverrides?: Record<string, string>,
    confirmedOverrides?: string[],
  ): Observable<ImportResult> {
    const form = new FormData();
    form.append('file', file, file.name);
    if (nameOverrides && Object.keys(nameOverrides).length > 0) {
      form.append('name_overrides', JSON.stringify(nameOverrides));
    }
    if (confirmedOverrides && confirmedOverrides.length > 0) {
      form.append('confirmed_overrides', JSON.stringify(confirmedOverrides));
    }
    const url =
      `${this.apiUrl}/imports/${kind}` +
      `?dry_run=${dryRun ? 'true' : 'false'}` +
      `&has_header=${hasHeader ? 'true' : 'false'}`;
    return this.http.post<ImportResult>(url, form);
  }

  getRecalcStatus(): Observable<RecalcStatus> {
    return this.http.get<RecalcStatus>(`${this.apiUrl}/imports/recalc/status`);
  }

  triggerRecalc(range?: { start_date?: string; end_date?: string }): Observable<RecalcTriggerResponse> {
    return this.http.post<RecalcTriggerResponse>(`${this.apiUrl}/imports/recalc`, range ?? {});
  }

  getNetworthHistory(from?: string, to?: string, interval: 'day' | 'week' | 'month' = 'day'): Observable<NetworthPoint[]> {
    let params: HttpParams | undefined;

    if (from) {
      params = (params ?? new HttpParams()).set('from', from);
    }

    if (to) {
      params = (params ?? new HttpParams()).set('to', to);
    }

    if (interval !== 'day') {
      params = (params ?? new HttpParams()).set('interval', interval);
    }

    return this.http.get<NetworthPoint[]>(`${this.apiUrl}/history`, params ? { params } : {});
  }

  getUpcomingEvents(from?: string): Observable<UpcomingEvent[]> {
    const params = from ? new HttpParams().set('from', from) : undefined;
    return this.http.get<UpcomingEvent[]>(
      `${this.apiUrl}/upcoming-events`,
      params ? { params } : {},
    );
  }

  getSymbolNames(): Observable<Record<string, string>> {
    return this.http.get<Record<string, string>>(`${this.apiUrl}/symbol-map/names`);
  }

}
