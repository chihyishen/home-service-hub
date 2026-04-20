export enum TransactionType {
  BUY = 'BUY',
  SELL = 'SELL'
}

export interface Transaction {
  id: number;
  symbol: string;
  name?: string;
  type: TransactionType;
  quantity: number;
  price: number;
  trade_date?: string | Date;
  fee: number;
  tax: number;
  created_at?: string;
  updated_at?: string;
}

export interface Dividend {
  id: number;
  symbol: string;
  amount: number;
  ex_dividend_date: string | Date;
  received_date?: string | Date;
  created_at?: string;
  updated_at?: string;
}

export interface StockHolding {
  symbol: string;
  name?: string;
  total_quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  day_change_amount: number;
  day_change_percent: number;
  day_pnl: number;
  total_dividends: number;
  total_pnl_with_dividend: number;
  xirr?: number;              // 年化報酬率，e.g. 0.1523 = 15.23%
}

export interface PortfolioSummary {
  total_market_value: number;
  total_cost: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_percent: number;
  total_day_pnl: number;
  total_dividends: number;
  holdings: StockHolding[];
  portfolio_xirr?: number;    // 整體投資組合年化報酬率
}

export interface ExDividendRecord {
  symbol: string;
  name: string;
  ex_dividend_date?: string;
  ex_rights_date?: string;
  cash_dividend?: string;
  stock_dividend?: string;
}
