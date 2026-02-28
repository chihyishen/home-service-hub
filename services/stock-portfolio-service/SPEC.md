# Home Service Hub - 投資組合 (Stock Portfolio) API 規格與使用說明書

## 1. 專案概述
本服務旨在提供使用者管理台股投資組合的功能。透過串接台灣證券交易所 (TWSE) 的即時報價 API，自動計算持股成本、市值、未實現損益以及含息損益。

## 2. 系統架構
- **服務名稱**: `stock-portfolio-service`
- **技術棧**: FastAPI (Python), SQLAlchemy (ORM), PostgreSQL (Database)
- **外部依賴**: TWSE MIS API (即時股價來源)
- **監聽埠**: `8001` (透過 PM2 啟動)
- **前端路徑**: `/portfolio` (Angular 儀表板), `/portfolio/transactions` (交易紀錄)

## 3. API 規格說明

### 3.1 投資組合總覽 (Summary)
- **Endpoint**: `GET /api/portfolio/summary`
- **功能**: 回傳目前所有持股的加權平均成本、即時股價、總市值、損益統計。
- **回傳內容摘要**:
  - `total_market_value`: 總市值
  - `total_cost`: 總原始成本
  - `total_unrealized_pnl`: 總未實現損益
  - `total_day_pnl`: 投資組合今日總損益。
  - `holdings`: 各別股票清單 (包含 `symbol`, `name`, `avg_cost`, `current_price`, `day_pnl` 等)。

### 3.2 交易紀錄管理 (Transactions)
- **Endpoints**: 
  - `POST /api/portfolio/transactions`: 新增交易紀錄。
  - `GET /api/portfolio/transactions`: 查詢完整交易清單。
  - `PUT /api/portfolio/transactions/{id}`: 修改現有交易紀錄。
  - `DELETE /api/portfolio/transactions/{id}`: 刪除交易紀錄。
- **強化特性**:
  - **代碼寬容處理**: 自動移除 `.TW` 或 `.TWO` 後綴，確存入資料庫之代碼為純數字。
  - **歷史日期支援**: 新增 `trade_date` 欄位，支援補錄過往交易紀錄（如未提供則預設為當前時間）。
- **欄位**: 
  - `symbol`: 股票代碼 (例如: 2330, 0050.TW)
  - `type`: `BUY` (買進) 或 `SELL` (賣出)
  - `quantity`: 股數
  - `price`: 成交單價
  - `trade_date`: 交易時間 (選填)
  - `fee`/`tax`: 手續費與交易稅 (選填)

### 3.3 現金股利紀錄 (Dividends)
- **Endpoints**:
  - `POST /api/portfolio/dividends`: 新增股利紀錄。
  - `GET /api/portfolio/dividends`: 查詢股利清單。
  - `PUT /api/portfolio/dividends/{id}`: 修改股利紀錄。
  - `DELETE /api/portfolio/dividends/{id}`: 刪除股利紀錄。
- **欄位**:
  - `symbol`: 股票代碼
  - `amount`: 發放總金額
  - `ex_dividend_date`: 除息日

## 4. 使用說明

### 4.1 如何開始使用
1. **進入導航**: 開啟首頁後，點擊左側選單的「**投資理財**」>「**投資組合**」。
2. **新增第一筆交易**: 點擊「**股票交易紀錄**」，進入後點擊「**新增交易**」。輸入股票代碼（如：`2330`）、股數與單價後儲存。
3. **查看損益**: 回到「**投資組合**」儀表板，系統將自動從 TWSE 抓取即時股價並顯示您的賺賠狀況。

### 4.2 損益計算規則
- **平均成本 (Avg Cost)**: `(成交單價 * 成交股數 + 手續費) / 總股數`。
- **未實現損益**: `(即時股價 * 持股數) - 總持股成本`。
- **單日損益 (Day P/L)**: `(即時股價 - 昨收價) * 持股數`。
- **含息總損益**: `未實現損益 + 已領取現金股利`。
- **色彩標示**: 符合台灣市場習慣，**紅色**代表獲利/上漲，**綠色**代表虧損/下跌。

## 5. 開發者筆記 (AI Agent Skill Context)
- **即時報價機制**: 系統會同時查詢 `tse` (上市) 與 `otc` (上櫃) 標籤。
- **可觀測性**: 整合 OpenTelemetry。若要觀察 API 效能，請至 Grafana 查詢 `stock-portfolio-service` 標籤的 Trace。
- **資料庫擴充**: 若需修改模型，請編輯 `services/stock-portfolio-service/app/models/portfolio.py` 並重啟 PM2 服務。

## 6. 疑難排解
- **股價沒更新?**: 確認伺服器是否可連外網，且 TWSE API 沒被封鎖。
- **找不到股票?**: 請確認輸入的是純數字代碼 (2330)，目前僅支援台股。
