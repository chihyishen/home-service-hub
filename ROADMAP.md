# 🗺️ Home Service Hub Roadmap

這份 roadmap 以家用、單機部署的實際需求為準。架構會保留清楚的服務邊界，但不為尚未出現的高併發、可靠事件投遞或多實例一致性需求預先增加基礎設施。

## ✅ 已完成：可用的家庭服務中樞

- [x] **核心服務**：庫存、記帳與台股投資組合各自提供 API 與資料模型。
- [x] **統一入口**：Angular frontend 與 Spring Cloud Gateway 提供瀏覽器及 AI Agent 的單一入口。
- [x] **認證與授權**：Keycloak、OIDC/JWT、PKCE、service account、scope 路由及後端雙層驗證。
- [x] **資料與物件儲存**：PostgreSQL 儲存業務資料；MinIO 儲存庫存圖片，瀏覽器經同源 `/minio` 路徑存取。
- [x] **排程與短期快取**：台股服務以 APScheduler 執行行情、股利與快照工作，並以 in-process cache 降低外部 API 請求。
- [x] **診斷基礎**：OpenTelemetry Collector 將 logs 送至 Loki、traces 送至 Tempo，並由 Grafana 統一查閱。

## 🟡 近期：操作性與可靠性

- [x] **Grafana Operations dashboard**：已驗證服務篩選、錯誤／警告、即時日誌查詢，以及 Loki 重啟後的資料持久性。
- [ ] **備份與還原演練**：記錄並驗證 PostgreSQL、MinIO、Keycloak 與必要設定的家庭環境復原流程。
- [ ] **排程結果可見性**：讓每日行情、股利與資產快照工作的開始、完成、筆數、耗時及失敗原因能從結構化日誌快速查找。

## 🟣 下一階段：跨服務業務整合

- [ ] **投資與記帳串接**：將股票買賣、股利及相關現金流連動至記帳服務。第一版採同步 API，讓使用者能立即知道成功或失敗。
- [ ] **重複執行保護**：為跨服務寫入定義 idempotency key、重試邊界與人工修復方式，避免重複記帳。
- [ ] **可追查的業務鏈**：實作上述流程時，補齊 Browser／Agent → Gateway → backend 的 trace propagation，並建立對應 Grafana 操作視圖。

## 🔵 需求出現後再評估

- **背景工作佇列**：只有在工作不能遺失、必須可靠重試、或同步等待已不可接受時才導入。
- **共享快取／共享限流狀態**：只有在多實例部署或量測確認瓶頸後才導入。
- **完整 metrics 與告警系統**：只有在需要長期趨勢、SLO、容量規劃或主動告警時才導入。

每一項新基礎設施都必須對應一個已確認的使用情境、失敗模式與驗收方式；學習性實驗可獨立保存，不必成為核心服務的常駐依賴。
