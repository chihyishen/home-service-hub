# 🗺️ Project Roadmap - Home Inventory System

這個文件記錄了系統從基礎建設到企業級架構的演進路徑。我們目前的進度已完成 **Phase 0**。

---

## 🟢 Phase 0: 基礎建設與可觀測性 (Completed)
*打好地基，確保開發流暢且系統透明。*
- [x] **Docker 化基礎設施**: PostgreSQL, MinIO, RabbitMQ, Grafana (LGTM Stack)。
- [x] **環境變數同步機制**: 實作 `.env` 單一來源，跨 Java 與 Angular 自動同步。
- [x] **全鏈路分散式追蹤 (E2E Tracing)**: 實作 Browser -> Dev Proxy -> Spring Boot -> DB 的追蹤。
- [x] **開發無痕化**: 透過 Proxy 解決遠端開發連線問題，不暴露敏感 IP。

---

## 🟡 Phase 1: 核心業務與系統強健性 (Active)
*讓現有的 CRUD 具備生產等級的穩定度。*
- [ ] **後端精細化驗證 (Validation)**: 使用 `jakarta.validation` 確保數據完整性。
- [ ] **全域錯誤處理 (Global Exception Handling)**: 實作標準化錯誤響應格式。
- [ ] **前端響應式表單 (Reactive Forms)**: 優化 `item-form`，整合後端驗證錯誤顯示。
- [ ] **單元測試與集成測試**: 補齊核心 Service 的 JUnit 5 測試。

---

## 🔵 Phase 2: 非文字數據與物件儲存
*引入圖片管理，增加庫存系統的實用性。*
- [ ] **MinIO 整合**: 實作圖片/文件上傳介面與 API。
- [ ] **Presigned URLs**: 實作安全的私有圖片存取機制。
- [ ] **檔案處理服務**: 實作縮圖生成或格式轉換。

---

## 🟣 Phase 3: 異步架構與微服務解耦
*邁向事件驅動架構 (Event-Driven Architecture)。*
- [ ] **RabbitMQ 整合**: 實作核心業務的 Domain Events。
- [ ] **Audit Service**: 建立獨立的審計微服務，非同步記錄系統變動。
- [ ] **跨服務追蹤挑戰**: 實作 Trace Context 透過 Message Queue 傳遞。

---

## 🔴 Phase 4: 效能優化與邊界安全
*處理高併發情境與系統防禦。*
- [ ] **Redis Caching**: 為熱門查詢實作快取機制。
- [ ] **API Gateway**: 使用 Spring Cloud Gateway 統一入口。
- [ ] **Rate Limiting**: 實作 API 限流防止暴力攻擊。
- [ ] **性能監控儀表板**: 在 Grafana 實作前端 RUM (Real User Monitoring) 面板。
