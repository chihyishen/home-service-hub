# 家用庫存系統設計方案（以現有 `Item CRUD` 為基礎的 MVP → 可擴充版本）

## 摘要
基於你目前在 `/Users/chihyi/projects/home-service-hub/README.md` 與 `/Users/chihyi/projects/home-service-hub/services/inventory-api/item-service` 的現況（已有 `Item` CRUD、分類/位置、圖片上傳、Angular 清單頁），建議先做一個「日用品為主、數量追蹤、補貨與盤點優先」的家用庫存 MVP。

核心原則：
- 先保留你現在的 `Item` 單表心智模型（好上手）
- 但資料設計改成「主檔 + 異動紀錄」以避免未來卡住
- 優先解決真實家庭使用價值：缺貨提醒、快速扣補量、採買清單、盤點落差

---

## 設計目標（本次規劃已鎖定）
- 目標使用者：單一家庭（你自己/家人）
- 主要場景：補貨與盤點
- 範圍：日用品（衛生紙、洗髮精、清潔用品、備品等）
- 追蹤粒度：數量 + 低庫存提醒（不做批次/效期）
- 成功標準：
  - 能快速新增品項與收納位置
  - 能進行「使用/補貨/盤點修正」並保留歷史
  - 能自動產生低庫存清單與採買清單
  - UI 可在手機上快速操作（家庭場景常用手機）

---

## 系統概念模型（建議）
目前 `Item.quantity` 是快照值；建議演進為：

1. `Item`（品項主檔）
- 是什麼：品項定義與目前狀態摘要
- 用途：列表顯示、搜尋、分類、位置、低庫存判斷

2. `InventoryTransaction`（庫存異動紀錄）
- 是什麼：每次增減量與原因（使用/補貨/盤點）
- 用途：可追蹤歷史、分析消耗速度、回溯錯誤

3. `ShoppingListItem`（採買清單）
- 是什麼：待購買品項（可由低庫存自動建立）
- 用途：把「提醒」變成「可執行清單」

4. `InventoryAlert`（可選，MVP 可不落表）
- 是什麼：低庫存/異常提醒事件
- 用途：日後接通知（LINE/Email/Push）

---

## 建議資料表/欄位（MVP）
### 1. `items`（保留並擴充）
在現有 `/Users/chihyi/projects/home-service-hub/services/inventory-api/item-service/src/main/java/com/inventory/item/model/Item.java` 基礎上增加：

- `skuCode`（可空，家庭自訂代碼）
- `unit`（例如 `pcs`, `bottle`, `roll`, `pack`）
- `minQuantity`（低庫存門檻）
- `targetQuantity`（理想庫存量，用於補貨建議）
- `isConsumable`（預設 `true`）
- `status`（`ACTIVE` / `ARCHIVED`）
- `lastRestockedAt`（最近補貨時間，可由異動回填）
- `version`（樂觀鎖，可選）

保留現有欄位：
- `name`, `category`, `location`, `quantity`, `note`, `imageUrl`, `createdAt`, `updatedAt`

### 2. `inventory_transactions`（新增）
欄位建議：
- `id`
- `item_id` (FK)
- `type` (`CONSUME`, `RESTOCK`, `ADJUST`)
- `delta_quantity`（可正可負）
- `before_quantity`
- `after_quantity`
- `reason`（文字，盤點備註/補貨來源）
- `source` (`MANUAL`, `SYSTEM`)
- `operator_name`（先字串即可，MVP 無登入）
- `occurred_at`
- `created_at`

### 3. `shopping_list_items`（新增）
欄位建議：
- `id`
- `item_id` (FK, 可空；若已刪除品項仍保留文字)
- `item_name_snapshot`
- `suggested_quantity`
- `status` (`PENDING`, `PURCHASED`, `SKIPPED`)
- `source` (`LOW_STOCK_RULE`, `MANUAL`)
- `note`
- `created_at`
- `updated_at`

---

## 主要流程設計（使用者角度）
### A. 新增品項（MVP）
- 輸入：名稱、分類、位置、目前數量、單位、低庫存門檻、理想庫存
- 可選：圖片、備註
- 建立後：若 `quantity <= minQuantity`，即標記為低庫存

### B. 快速扣庫（使用）
- UI 清單每列提供 `-1` / `-N` 快速按鈕
- 後端建立 `CONSUME` 異動並回寫 `items.quantity`
- 若扣完低於門檻：
  - 顯示警示
  - 可一鍵加入採買清單（或自動建立）

### C. 補貨
- 從採買清單或 item 詳細頁執行補貨
- 輸入補貨量（例如 +6）
- 建立 `RESTOCK` 異動、更新目前庫存
- 自動更新 `lastRestockedAt`

### D. 盤點修正
- 盤點時直接輸入「實際數量」
- 系統自動換算差額並建立 `ADJUST` 異動
- 保留原因（例：漏記、家人已使用）

### E. 採買清單生成
- 規則（MVP）：
  - `quantity <= minQuantity`
  - 建議補貨量 = `targetQuantity - quantity`（至少 1）
- 避免重複：
  - 同一 item 若已有 `PENDING` 採買項目，不重複新增

---

## 前端 UX 規劃（Angular）
以你現有 `/Users/chihyi/projects/home-service-hub/frontend/src/app/components/item-list/item-list.ts` 為核心延伸，先不大改頁面架構。

### MVP 頁面/區塊
1. `Item List`（現有頁面升級）
- 新增欄位：`unit`, `minQuantity`, `targetQuantity`
- 視覺狀態：
  - 正常
  - 低庫存（紅/橘 tag）
  - 無庫存（更醒目）
- 列操作：
  - 快速扣 1
  - 快速補貨
  - 盤點修正
  - 查看歷史

2. `Shopping List`（新頁）
- 顯示待購買項目
- 勾選已購（可觸發補貨流程或標記完成）
- 手動新增採買項目（非庫存品也可）

3. `Item Detail / History Drawer`（可先用對話框）
- 顯示最近異動紀錄
- 顯示近期消耗趨勢（先文字摘要即可）

### 手機優先操作
- 列表卡片模式（手機）
- 大按鈕 `使用 -1` / `補貨`
- 減少表單欄位一次輸入負擔（分段顯示）

---

## 後端 API / 介面變更（重要）
### 現有 API（保留）
- `GET /api/items`
- `GET /api/items/{id}`
- `POST /api/items`
- `PUT /api/items/{id}`
- `DELETE /api/items/{id}`
- `POST /api/items/{id}/image`
- `GET /api/items/categories`
- `GET /api/items/locations`

### 新增或調整 API（MVP）
#### Item 查詢/主檔
- `GET /api/items?keyword=&lowStockOnly=&category=&location=`
- `POST /api/items`
  - 請求新增欄位：`unit`, `minQuantity`, `targetQuantity`, `isConsumable`
- `PUT /api/items/{id}`
  - 同上

#### 庫存異動（核心）
- `POST /api/items/{id}/transactions`
  - request:
    - `type`
    - `deltaQuantity`（CONSUME/RESTOCK）
    - `actualQuantity`（ADJUST 用）
    - `reason`
    - `operatorName`
  - response:
    - 更新後 `ItemResponse`
    - 異動摘要
- `GET /api/items/{id}/transactions?limit=50`
  - 顯示歷史

#### 快速操作（可選，讓前端更簡單）
- `POST /api/items/{id}/consume`
- `POST /api/items/{id}/restock`
- `POST /api/items/{id}/adjust`

#### 採買清單
- `GET /api/shopping-list?status=PENDING`
- `POST /api/shopping-list/generate-from-low-stock`
- `POST /api/shopping-list`
- `PATCH /api/shopping-list/{id}`（更新狀態）
- `DELETE /api/shopping-list/{id}`（可選）

### DTO / 型別變更
- `ItemRequest` 新增：
  - `unit`, `minQuantity`, `targetQuantity`, `isConsumable`
- `ItemResponse` 新增：
  - `unit`, `minQuantity`, `targetQuantity`, `isLowStock`, `stockStatus`
- 新增：
  - `InventoryTransactionRequest/Response`
  - `ShoppingListItemRequest/Response`

---

## 商業規則（Decision Complete）
### 庫存計算規則
- `CONSUME`: `after = before - delta`
- `RESTOCK`: `after = before + delta`
- `ADJUST`: `after = actualQuantity`
- 不允許 `after < 0`（MVP 預設）
- `deltaQuantity` 必須 > 0（由 `type` 決定加減語意）

### 低庫存規則
- `quantity <= minQuantity` 視為低庫存
- `quantity == 0` 視為缺貨（比低庫存更高優先）
- 若 `minQuantity` 為空，則不判斷低庫存（MVP 可允許）

### 採買建議量
- 若有 `targetQuantity`：`max(target - current, 1)`
- 若無 `targetQuantity`：預設 `1`

### 刪除策略
- `DELETE /api/items/{id}`：
  - MVP 可實刪，但建議改 `ARCHIVED`
  - 若已有交易紀錄，優先 `ARCHIVED` 避免歷史斷裂

---

## 與現有系統的整合建議（你的專案亮點）
### 1. Observability（你 README 的主軸）
為庫存流程加可觀測性（很加分）：
- Trace span：
  - `item.create`
  - `inventory.consume`
  - `inventory.restock`
  - `shopping-list.generate`
- Metrics：
  - `inventory_low_stock_items_count`
  - `inventory_transactions_total{type=...}`
  - `shopping_list_pending_count`
- Logs：
  - 盤點修正（`ADJUST`）記錄 before/after/reason（避免誤操作難追）

### 2. Accounting Service（後續 phase）
先不耦合，但預留事件/欄位：
- 補貨時可選填金額與通路（未來同步記帳）
- 或由 accounting 記帳後反向建議補貨成本分析

---

## 實作分期（建議順序）
### Phase 1: MVP（最值得先做）
- `Item` 擴欄位（單位/門檻/理想量）
- 新增 `InventoryTransaction`
- 新增異動 API（至少一個通用 transaction endpoint）
- 前端加快速扣庫/補貨/盤點
- 低庫存標示與篩選
- 採買清單（基本版）

### Phase 2: 使用體驗強化
- 手機操作優化（卡片模式/大按鈕）
- 異動歷史視圖
- 批次盤點模式（逐項輸入實際數量）
- 自動產生採買清單排程（手動觸發也可）

### Phase 3: 智慧化與跨服務
- 消耗速度估算（預估可用天數）
- 補貨建議排序（即將用完優先）
- 與記帳服務串接採買紀錄
- 通知（LINE/Email/Web Push）

---

## 測試案例與驗收情境（必要）
### 後端單元/整合測試
1. 建立品項時低庫存判斷正確
2. `CONSUME` 後 quantity 正確遞減並寫入 transaction
3. `RESTOCK` 後 quantity 正確遞增並更新 `lastRestockedAt`
4. `ADJUST` 以實際數量覆蓋並保留 before/after
5. 禁止扣到負數（回 400）
6. 低庫存生成採買清單不重複
7. 刪除/封存有交易紀錄品項不破壞歷史查詢
8. 關鍵字 + `lowStockOnly` 篩選可同時使用

### 前端情境測試
1. 在列表頁快速 `-1` 成功且 UI 即時更新
2. 低庫存 tag 顯示正確
3. 盤點修正輸入實際數量後，列表數量更新
4. 採買清單勾選已購後狀態更新
5. 手機版操作按鈕不擁擠且可點擊

### 驗收（你日常使用）
- 新增 10 個日用品後，能在 1 分鐘內完成一次「使用 + 補貨 + 看低庫存」
- 任一品項可查到最近 5 筆異動原因
- 低庫存清單能直接轉成採買清單，不需重複輸入名稱

---

## 重要介面/型別變更摘要（實作者必看）
- `Item` entity / DTO 新增：`unit`, `minQuantity`, `targetQuantity`, `isConsumable`
- 新增 entity：`InventoryTransaction`
- 新增 entity：`ShoppingListItem`
- `ItemResponse` 新增衍生欄位：`isLowStock`, `stockStatus`
- 新增 API 群組：`/api/items/{id}/transactions`, `/api/shopping-list`
- 前端 `ItemRequest` / `ItemResponse` 型別同步擴充（`/Users/chihyi/projects/home-service-hub/frontend/src/app/models/item.model.ts`）

---

## 假設與預設（已替你先做決策）
- 單一家庭、無登入權限系統（`operatorName` 用字串先代替）
- 不做效期/批次/條碼掃描（先聚焦可用性）
- 不做多單位換算（例如 箱→包→個）
- 不做自動通知（先做 UI 低庫存 + 採買清單）
- 不與記帳服務同步寫入（先鬆耦合，預留擴充點）
- 刪除策略預設改為「封存優先」而非實刪（避免歷史遺失）

