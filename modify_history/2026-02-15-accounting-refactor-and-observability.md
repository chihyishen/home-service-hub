# 修改紀錄 - 2026-02-15 (會計服務重構、全域變數整頓與可觀測性強化)

## 📋 概述
今日完成了 `accounting-service` 的深度重構與命名統一，建立了「全域單一配置來源 (.env)」機制，並成功實作了跨語言（Java & Python）的 OpenTelemetry 監控整合。

## 📅 日期
2026-02-15

## 🔍 遇到了什麼問題？ (Problem Statement)
- **架構雜亂**：原 Python 服務功能混雜，缺乏標準的三層架構與 CRUD 完整性。
- **可觀測性斷層**：Python 服務無法在 Grafana 中與日誌聯動，且 Trace 層次不清（看不見 Body 與 Service 邏輯）。
- **環境變數混亂**：各服務對環境變數依賴不一，存在預設值導致配置不透明，且 Java 與 Python 的 OTel 傳輸協定（gRPC vs HTTP）發生衝突。
- **路徑計算錯誤**：Python 服務在載入根目錄 `.env` 時，層次計算錯誤導致配置失效。

## 💡 解決方案 (Solution & Implementation)

### 1. 核心策略
- **領域驅動重構**：將 Python 服務拆分為 `Router-Service-Model`，並實作軟刪除與月度報表邏輯。
- **配置現代化**：整頓全域 `.env`，採用 `load_dotenv(override=True)` 確保 `.env` 為唯一真理，並移除程式碼中的所有預設值。
- **雙協議共存**：針對 Java 穩定性保留 **HTTP (4318)**，針對 Python 效能啟用 **gRPC (4317)**，透過獨立變數互不干擾。

### 2. 實作細節
- **Python**: 
    - 遷移至 `accounting-service` 資料夾。
    - 補齊 `is_deleted` 與 `transaction_type` 欄位及自動資料庫修復。
    - 手動儀表化 Service 層與 Router 層，記錄 Request/Response Body。
- **Java**: 
    - 服務名稱同步為 `inventory-item-service`。
    - Swagger 文件全面中文化並對齊命名規範。
- **OpenTelemetry**: 使用最新 SDK (1.30+) 的 `OTLPSpanExporter` 與 `OTLPLogExporter` 實作日誌聯動。

---

## 📂 關鍵設定檔變動 (Key Code Snippets)

### `.env` (全域統一配置)
```bash
# Java 優先使用 HTTP (4318)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
# Python 優先使用 gRPC (4317)
OTEL_EXPORTER_OTLP_ENDPOINT_PYTHON=http://localhost:4317
```

### `app/database.py` (嚴格環境變數模式)
```python
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env"))
load_dotenv(env_path, override=True)
# 若缺失變數則直接拋出 ValueError 阻斷啟動
```

---

## ✅ 驗證結果 (Verification)
- [x] **API 穩定性**：通過整合測試，確認收支、報表與軟刪除邏輯正常。
- [x] **環境變數驗證**：確認 Java 與 Python 均能正確讀取對應的資料庫與 OTel 配置。
- [x] **追蹤深度化**：在 Tempo 中可看到 `router -> service -> sql` 層次及完整的 JSON 內容。
- [x] **標籤聯動**：Loki 與 Tempo 成功透過 `service_name="accounting-service"` 進行跳轉。

## 🚀 後續行動 (Next Steps) / ⚠️ 注意事項
- **Pull Request**：代碼已推送到 `feat/accounting-refactor-observability` 分支。
- **本地文件**：`規格書.md` 已保留於本地，用於後續開發。
- **Java 重啟**：若修改了配置，請執行 `./gradlew clean :item-service:bootRun` 以清理快取。
