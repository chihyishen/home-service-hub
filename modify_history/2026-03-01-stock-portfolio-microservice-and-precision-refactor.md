# 修改紀錄 - 2026-03-01 (投資組合微服務上線與金融精度重構)

## 📋 概述
新增獨立的「投資組合 (Stock Portfolio)」微服務，整合 TWSE 即時報價，並針對全系統金錢運算進行 `Decimal` 高精度重構，同時完成前端儀表板開發與資料庫命名標準化。

## 📅 日期
2026-03-01

## 🔍 遇到了什麼問題？ (Problem Statement)
- **資產管理缺失**：原本系統缺乏股票投資追蹤功能，無法即時獲取台股報價。
- **計算精度異常**：使用 `float` 處理股價與成本，導致出現 `23.459999` 類型的二進位誤差，造成對帳不齊。
- **UI 空間不足**：Dashboard 卡片標題過長（如：未實現損益(不含息)）導致折行，且缺乏靈活的顯示維度。
- **環境不一致**：`accounting-service` 使用 Python 3.13 而新服務誤用 3.9；資料庫命名（`agent_accounting_db`）不夠直觀。

## 💡 解決方案 (Solution & Implementation)

### 1. 建立 Stock Portfolio 微服務 (FastAPI + Python 3.13)
- **即時報價**：實作 `twse_service.py` 串接證交所 API，具備多重價格備援 (z > pz > y) 與上市櫃自動匹配。
- **券商口徑**：加入賣出成本估算（手續費 2.8 折、證交稅 0.1%），使「淨市值」與真實損益對齊。

### 2. 金融級精度重構 (De-float Refactor)
- **後端**：全面改用 `decimal.Decimal` 取代 `float`。DB 欄位轉為 `Numeric(12, 2)`。
- **運算**：嚴格使用字串初始化 `Decimal(str(val))` 並採用 `ROUND_HALF_UP` 捨入規則。
- **前端**：修正 Angular 範本，改用 `number` pipe 處理 Decimal 序列化後的字串，移除報錯的 `.toFixed()`。

### 3. 前端儀表板與互動優化
- **五大指標**：動態展示總市值、總成本、未實現損益、今日損益、累計股利。
- **視角切換**：實作「含息/不含息」動態切換按鈕，點擊即時重算損益與百分比，兼顧功能與排版美觀。
- **色彩規範**：套用台股「紅漲綠跌」視覺標準。

---

## 📂 關鍵設定檔變動 (Key Code Snippets)

### `portfolio_service.py` (高精度運算)
```python
# 估算券商賣出成本
def _estimate_sell_costs(gross_market_value: Decimal) -> Decimal:
    fee = (gross_market_value * Decimal("0.001425") * Decimal("0.28")).quantize(Decimal("1"), rounding=ROUND_DOWN)
    tax = (gross_market_value * Decimal("0.001")).quantize(Decimal("1"), rounding=ROUND_DOWN)
    return fee + tax

# 計算未實現損益
unrealized_pnl = (market_value - h["total_cost"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

### `dashboard.html` (動態視角切換)
```html
<p-button 
  [icon]="showWithDividend() ? 'pi pi-percentage' : 'pi pi-money-bill'" 
  (onClick)="toggleDividend()"
  [pTooltip]="showWithDividend() ? '目前顯示：含息損益' : '目前顯示：價差損益 (不含息)'">
</p-button>
```

---

## ✅ 驗證結果 (Verification)
- [x] **精度驗證**：00919 成本價精準顯示為 `23.45`，總計金額與券商對帳單完全一致。
- [x] **容錯驗證**：TWSE 盤後或維修時，系統自動抓取「昨收價」填充，持股不會消失。
- [x] **穩定性驗證**：全系統 Python 環境統一為 3.13，資料庫已成功更名為 `accounting_db`。

## 🚀 後續行動 (Next Steps)
- 觀察 TWSE API 調用頻率，若使用者增加需考慮實作 Redis 快取。
- 準備與 OpenClaw (Stock Master Agent) 進行 API 整合測試。
