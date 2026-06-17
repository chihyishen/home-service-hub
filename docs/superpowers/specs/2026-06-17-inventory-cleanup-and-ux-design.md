# 庫存系統：欄位瘦身與 UX 改善

- 日期：2026-06-17
- 服務：`services/inventory-api`（Java / Spring Boot）、`frontend`（Angular + PrimeNG）
- 狀態：已通過 brainstorming 設計確認，待 user 覆核後進入規劃

## 背景與目標

庫存系統目前可用但「不好用」。經訪談釐清，使用者的核心情境與痛點為：

- 邊走邊用手機操作；存放位置只有 2~3 個，同類東西放一起。
- **第一次建檔太麻煩**（逐項手動點擊輸入）。此問題以「自然語言 → JSON → 既有 API 灌入」的人工流程解決，**不需要程式改動**，因此不在本 spec 的程式範圍內（見附錄 A）。
- 資料模型存在數個「存了但程式沒用到」的冗餘欄位。
- 既有 UI 有數個可快速改善的 UX 缺陷。

本 spec 涵蓋兩個獨立、可分批實作與驗證的工作：

- **Plan A — 資料模型瘦身**（後端為主 + 一支 DB migration）
- **Plan B — UI/UX 改善**（前端為主）

兩者相依性低，但 Plan B 的「卡片進度條改顯示數量」與 Plan A 移除 `targetQuantity` 有關聯，實作時 A 先於 B 較順。

## 非目標（YAGNI）

- 不做盤點模式（batch stocktake）UI —— 後續維護使用者選擇手動操作，現有單項異動足夠。
- 不做分類/位置篩選 chip —— 導航靠 Plan B 的「按位置分組」+ 既有搜尋框即足夠（位置才 2~3 個）。
- 不做批次新增 API —— 第一次建檔為一次性工作，沿用既有單筆 `POST /api/items` 由 agent loop 即可。
- 不做主清單分頁、不做封存（soft delete），維持硬刪。

---

## Plan A — 資料模型瘦身

### 決策：移除 4 個欄位

經逐欄盤點程式實際使用狀況，移除以下欄位：

| 欄位 | 移除理由 |
|---|---|
| `targetQuantity` | 僅用於卡片進度條；使用者選擇改為單純顯示數量，低庫存提醒靠 `minQuantity` 已足夠 |
| `isConsumable` | 死欄位：無任何邏輯分支、表單也無此欄 |
| `status` | 形同虛設：永遠為 `ACTIVE`，無封存流程，刪除為硬刪 |
| `lastRestockedAt` | 補貨時有寫入，但 UI 從未顯示 |

**保留**：`name`、`quantity`、`category`、`location`、`minQuantity`、`note`、`imageUrl`、`version`、`createdAt`、`updatedAt`，以及衍生回應欄位 `isLowStock`、`stockStatus`（由 `minQuantity` 計算，不受本次移除影響）。

### 影響範圍（後端）

- **DB migration**：新增 `V2__drop_unused_item_fields.sql`，`ALTER TABLE items DROP COLUMN` 四欄（`target_quantity`、`is_consumable`、`status`、`last_restocked_at`）。
- **`model/Item.java`**：移除四個欄位與相關 `@Builder.Default`。
- **`dto/ItemRequest.java`**：移除 `targetQuantity`、`isConsumable`、`status`（含 `@Min` 驗證）。
- **`dto/ItemResponse.java`**：移除 `targetQuantity`、`isConsumable`、`status`、`lastRestockedAt`。
- **`mapper/ItemMapper.java`**：移除對 `lastRestockedAt` 的 `@Mapping(ignore)`（欄位已不存在）；確認 `getStockStatus`/`isLowStock` 不受影響。
- **`service/impl/ItemServiceImpl.java`**：
  - `applyDefaultsAndValidate`：移除 `isConsumable` 預設與 `status` 預設、移除 `targetQuantity` 驗證。
  - `createTransaction` 的 `RESTOCK` 分支：移除 `item.setLastRestockedAt(...)`。
- **測試**：更新所有引用上述欄位的單元/整合測試與測試資料 builder。

### 影響範圍（前端，與 Plan B 重疊處）

- `models/item.model.ts`：`ItemRequest` / `ItemResponse` 型別移除四欄。
- `item-list.ts`：`resetNewItem()` 移除 `targetQuantity`、`isConsumable`、`status`；`saveItem()` payload 移除這些欄位；移除 `calculateStockPercentage()`（改見 Plan B）。
- `item-list.html`：移除新增/編輯 dialog 中的「理想庫存量」欄位。

### 驗收

- 後端測試全綠（`./gradlew :item-service:test`）。
- migration 在乾淨 DB 與既有資料上皆可套用（DROP COLUMN 對既有資料安全）。
- 前端 build + 既有測試通過（`npm run build`、`npm test`）。
- 手動：新增/編輯/刪除/補貨/使用-1/盤點修正 全流程正常，回應不再含已移除欄位。

---

## Plan B — UI/UX 改善

針對 `frontend/src/app/components/item-list`。各項彼此獨立，可逐項實作驗證。

### B1. 搜尋 debounce

- 現況：`item-list.html` 的搜尋框 `(ngModelChange)="loadItems()"`，每個按鍵都打一次 API。
- 改為：輸入停止 ~300ms 後才查詢（RxJS `debounceTime` 或 signal + timer）。
- 驗收：連續輸入「衛生紙」只觸發一次 API。

### B2. 刪除確認改用 PrimeNG ConfirmDialog

- 現況：`item-list.ts:deleteItem` 使用瀏覽器原生 `confirm()`（阻塞、樣式不一致、手機體驗差）。
- 改為：PrimeNG `p-confirmDialog` + `ConfirmationService`。
- 驗收：刪除時跳出 PrimeNG 風格確認框，取消不刪、確認才刪。

### B3. 清單按位置分組顯示

- 現況：`hub-inventory-grid` 為平鋪卡片，順序由後端回傳決定。
- 改為：依 `location` 分組，每組一個標題（如「主臥櫃子」「後陽台」），組內維持卡片排列；無位置者歸「未知位置」組。
- 分組在前端進行（沿用既有 `getAllItems` 回傳）。需與既有搜尋/低庫存篩選相容（先篩後分組）。
- 驗收：清單依位置出現分隔標題，找特定區域物品直覺。

### B4. 載入中 / 錯誤狀態

- 現況：`loadItems()` 期間畫面無回饋。
- 改為：載入中顯示 skeleton 或 spinner；錯誤時顯示可重試的錯誤區塊（沿用既有 toast 之外，給清單區一個 inline 狀態）。
- 驗收：慢速網路下有明確載入回饋；API 失敗有明確錯誤呈現。

### B5. 低庫存一鍵加入購物清單

- **後端已具備**：`POST /api/shopping-list/generate-from-low-stock`（已自動去重）。本項僅需前端串接。
- 改為：庫存頁（或低庫存篩選開啟時）提供一顆按鈕，呼叫該端點，成功後 toast 回報新增數量。
- 於 `frontend/src/app/services/shopping-list.service.ts` 新增呼叫 `generate-from-low-stock` 的方法，由 `item-list.ts` 注入使用。
- 驗收：按下按鈕後，低庫存品項出現在購物清單，重複呼叫不產生重複項。

### B6. 新增物品時即可上傳圖片

- 現況：圖片上傳 `p-fileUpload` 僅在 `@if (isEdit)` 顯示（`item-list.html`）；圖片上傳 API（`POST /api/items/{id}/image`）需要已存在的 `itemId`。
- 設計：建立流程改為「先建立物品取得 id → 再上傳圖片」兩步，於同一儲存動作內串接（使用者無感）。新增 dialog 顯示圖片上傳區，使用者選圖後，於 `saveItem()` 成功取得新 id 後自動接著上傳。
- 邊界：若只填資料不選圖，行為與現況一致；上傳失敗不影響物品已建立，僅 toast 提示圖片上傳失敗。
- 驗收：新增物品時可選圖，存檔後物品即帶圖片。

### Plan B 驗收（整體）

- `npm run build` 與 `npm test` 通過。
- 手動走查 B1~B6 各情境。

---

## 附錄 A：第一次建檔的自然語言流程（無程式改動，僅記錄）

非程式範圍，但與本次「處理庫存系統」同源，記錄以利後續：

1. 使用者於外部聊天視窗（如 Gemini）用既有 intake prompt，逐項口述家中物品。
2. 助理整理、覆核後輸出 JSON 陣列（key 對齊 `ItemRequest`：`name`/`quantity`/`location`/`category`/`minQuantity`/`note`，移除欄位後不再含 `targetQuantity`/`isConsumable`/`status`）。
3. 使用者將 JSON 交回，由 agent 逐筆呼叫既有 `POST /api/items` 灌入；寫入前先列預覽表供確認。

> 注意：Plan A 移除欄位後，intake prompt 與 JSON schema 應同步移除 `isConsumable` 等欄位，避免灌入被忽略的欄位。
