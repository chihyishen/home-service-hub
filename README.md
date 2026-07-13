# 🏠 Home Service Hub (家庭服務中樞)

![Java](https://img.shields.io/badge/Java-21-orange?logo=java)
![Spring Boot](https://img.shields.io/badge/Spring%20Boot-4.0.1-green?logo=springboot)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-blue?logo=fastapi)
![Angular](https://img.shields.io/badge/Angular-21-red?logo=angular)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)
![Observability](https://img.shields.io/badge/Observability-OTel%20%7C%20Loki%20%7C%20Tempo%20%7C%20Grafana-purple)

這是一個實際使用中的 **個人生活運算中樞**。系統從個人工具演進為由 AI Agent 驅動的自動化後端；架構以家用、單機部署的可靠性與可維護性為優先，並保留清楚的服務邊界，讓需求出現時可以漸進演進。

## 🏗 系統架構 (Architecture)

```mermaid
graph TD
    %% 1. 存取層
    subgraph Access_Layer [使用者與代理人層]
        UI[Angular Dashboard<br/>https :4200]
        Agent[Hermes AI Agent<br/>client credentials]
    end

    %% 2. 身分認證
    subgraph Identity [身分認證層]
        Keycloak[Keycloak 26<br/>https :8443]
        KCDB[(Keycloak<br/>PostgreSQL)]
    end

    %% 3. 閘道
    subgraph Gateway_Layer [閘道層]
        Proxy[Angular Dev Proxy<br/>同源轉發]
        Gateway[API Gateway :8088<br/>JWT 驗證 + scope 路由 + 限流]
    end

    %% 4. 服務層
    subgraph Service_Layer [微服務層]
        Inventory[Inventory API<br/>Java 21 / Spring Boot]
        Accounting[Accounting Service<br/>Python 3.13 / FastAPI]
        Stock[Stock Portfolio<br/>Python 3.13 / FastAPI]
    end

    %% 5. 資料層
    subgraph Data_Layer [持久化與儲存層]
        Postgres[(PostgreSQL)]
        MinIO[MinIO Object Storage]
    end

    %% 6. 可觀測性層
    subgraph Obs_Layer [診斷：Logs 與 Traces]
        Collector[OTel Collector]
        Grafana[Grafana Dashboard]
        Tempo[Tempo / Loki]
    end

    %% 認證流
    UI -.->|"登入跳轉 (OIDC + PKCE)"| Keycloak
    Agent -.->|"secret 換 token"| Keycloak
    Keycloak --> KCDB
    Keycloak -.->|"JWKS 公鑰"| Gateway

    %% 請求流（皆帶 Bearer token）
    UI --> Proxy
    Proxy --> Gateway
    Agent --> Gateway
    Gateway -->|REST| Inventory
    Gateway -->|REST| Accounting
    Gateway -->|REST| Stock

    Inventory --> Postgres
    Accounting --> Postgres
    Stock --> Postgres
    Inventory -.-> MinIO

    %% 可觀測性流
    Inventory -.->|OTLP| Collector
    Accounting -.->|OTLP| Collector
    Stock -.->|OTLP| Collector
    Collector --> Tempo
    Grafana -->|Query| Tempo
```

### 認證與閘道的分工

- **Keycloak（身分認證）**：唯一知道「你是誰」的元件。瀏覽器走 OIDC 授權碼流程（帳密 + 30/90 天 remember-me session）；機器（Hermes agent）走 client credentials（clientID + secret）。兩者拿到的都是 Keycloak 私鑰簽名的短效 JWT（300 秒），token 內含 scope（如 `accounting.read`）。
- **API Gateway（存取控制）**：所有 API 請求的單一入口。用 Keycloak 的 JWKS 公鑰離線驗證 token 簽名、時效與 audience，並依路由檢查 scope（例如 Hermes 的 token 只有 `accounting.*`，打 `/api/items` 會被 403），再加上 bucket4j 限流。驗證不回查 Keycloak，兩者執行期解耦。
- **後端服務**：各自內建 resource-server 驗證（`AUTH_ENFORCEMENT_ENABLED`，已全面開啟）——與 gateway 形成雙層防禦，無有效 token 時後端本身也會拒絕（fail-closed）。

## 🌟 亮點功能 (Features)

- **🤖 AI Agent First**: 服務設計之初即考量 AI Agent的調用需求，具備良好的 API 結構與錯誤回傳機制。Hermes agent 以專屬 service account（最小權限 scope）透過閘道記帳。
- **🔐 統一認證與閘道**: Keycloak (OIDC) 簽發短效 JWT，Spring Cloud Gateway 集中驗證簽名/audience/scope 並限流；前端經 keycloak-js 登入（HTTPS + PKCE），支援長效 remember-me session。
- **可追查的 Logs 與 Traces**: OpenTelemetry 將服務日誌送至 Loki、trace 送至 Tempo，再由 Grafana 統一查閱；用於除錯與追查跨服務流程，而不是收集所有 request body。
- **Python Logs 與 Traces**: Python 服務以標準 `logging` 搭配 OpenTelemetry 輸出日誌；FastAPI trace 只保留 request root span，省略 ASGI `send` / `receive` 細節與 `/health`，讓 Grafana 的結構更接近應用流程。
- **Streamer DVR operations**: `STREAMER_DVR_LOG_DIR` 預設指向相鄰的 `../streamer-dvr/logs/`；Compose 只會以 read-only 方式將它掛載給 OTel Collector。Collector 解析其中的 JSONL 業務事件後送入 Loki；Grafana 的 `Streamer DVR · Operations` 位於獨立 folder，SQLite 與 Streamer DVR Vue Logs 頁面不受影響。
- **AI 驅動記帳系統**: 支援自然語言解析，自動將口語化描述轉化為精確的財務交易。
- **智慧庫存與投資**: 整合物件儲存 (MinIO) 管理實體物資，並自動抓取即時台股數據；台股組合支援 CSV 匯入、每日 OHLC 回填、除權息事件抓取、減資/分割自動調整成本基礎，以及當沖標記推導。
- **In-process Scheduler**: 台股組合服務內建 APScheduler，每日 17:00 回補 TWSE/TPEx 收盤、盤中每 15 分鐘刷新報價、15:30 寫入淨值快照。可透過 `SCHEDULER_ENABLED=false` 關閉。

## 🚀 快速開始 (Getting Started)

### 1. 環境準備
- **配置環境變數**: `cp .env.example .env`，再替換其中的密碼、Keycloak client secret、固定 LAN IP 與公開 URL；請勿直接使用範例 placeholder。
- **準備 HTTPS 憑證**: 將本機信任的憑證與私鑰放在 `infra/keycloak/certs/keycloak.pem`、`infra/keycloak/certs/keycloak-key.pem`，並確認憑證涵蓋 `.env` 中的 `KEYCLOAK_PUBLIC_HOST`。
- **啟動基礎設施與身分服務**: `docker compose up -d && docker compose --profile identity up -d keycloak`

### 2. 啟動服務 (各服務目錄下執行)
- **Inventory**: `./gradlew :item-service:bootRun`
- **Accounting**: `uvicorn app.main:app --port 8000`
- **Stock**: `uvicorn app.main:app --port 8001`
- **Gateway**: `../inventory-api/gradlew -p . bootRun`（於 `services/gateway-service`）
- **Frontend**: `npm start`（HTTPS，入口 `https://<LAN-IP>:4200`）

或一次啟動全部：`npx pm2 start ecosystem.config.js`

> 認證相關：Keycloak 對外入口為 `https://<LAN-IP>:8443`。realm JSON 只在空 DB 時匯入；首次啟動後需建立 household administrator，既有 realm 的變更則透過 `kcadm` 套用。操作方式見 [`docs/security/keycloak-operations.md`](docs/security/keycloak-operations.md)。

### 3. Stock Portfolio 服務環境變數
- `SCHEDULER_ENABLED` (預設 `true`)：設 `false` 停用內建 APScheduler（測試 / CI 必設）。

服務細節（端點清單、Scheduler cron、Day-trade 推導規則等）見 [`services/stock-portfolio-service/README.md`](services/stock-portfolio-service/README.md)。

### 4. 本機安全預設

- Compose 發佈的基礎設施與後端服務預設只綁定 loopback。`INFRA_BIND_HOST` 控制 PostgreSQL、OTel、Tempo、Loki 與 MinIO；`APP_BIND_HOST` 控制三個後端 API。除非已有明確的防火牆或 Gateway 規則，請勿改成 `0.0.0.0`。
- Grafana 固定保留 `127.0.0.1:3000`，並可透過 `GRAFANA_VPN_BIND_HOST` 增加第二個受信任入口。當 WireGuard Server 位於家用路由器時，將它設成主機的 LAN IP；本機目前使用 `192.168.0.100`，VPN client 即可開啟 `http://192.168.0.100:3000`。這個入口不經過 Gateway，且不會連帶開放其他基礎設施服務。
- PM2 啟動的 Accounting、Stock backends 與 Gateway 都只綁定 `127.0.0.1`；Frontend（HTTPS）維持 VPN/LAN 可達，作為唯一瀏覽器入口，API 流量經其 proxy 進入 Gateway。Keycloak 綁定 LAN（`IDENTITY_BIND_HOST`），供瀏覽器登入跳轉使用。
- Inventory 在本機直接啟動時由 `INVENTORY_SERVER_ADDRESS` 控制監聽位址，預設 `127.0.0.1`。Compose 會在容器內覆寫為 `0.0.0.0`，但 host 端仍只發佈至 `APP_BIND_HOST`。
- Inventory 的 OpenAPI 與 Swagger UI 預設關閉。僅在受信任的除錯環境設 `INVENTORY_API_DOCS_ENABLED=true` 開啟。
- SQL query text、parameter values 與 query arguments 預設不進入觀測資料。除錯時可分別使用 `INVENTORY_SQL_QUERY_TEXT_ENABLED`、`INVENTORY_SQL_PARAMETER_VALUES_ENABLED`、`INVENTORY_SQL_QUERY_ARGUMENTS_ENABLED` 顯式開啟；Hibernate SQL logger 另由 `INVENTORY_HIBERNATE_SQL_LOG_LEVEL` 控制，預設 `OFF`。這些內容可能包含敏感資料。
- HTTP query string、request payload 與 Logbook 完整 request/response logging 預設關閉。僅在受信任的短期除錯環境分別使用 `INVENTORY_HTTP_QUERY_LOGGING_ENABLED=true`、`INVENTORY_HTTP_PAYLOAD_LOGGING_ENABLED=true` 或調高 `INVENTORY_LOGBOOK_LOG_LEVEL`；完成後應立即恢復安全預設。
- `MINIO_ENDPOINT=http://127.0.0.1:9000` 是 Inventory backend SDK 使用的內部端點；`MINIO_PUBLIC_ENDPOINT=/minio` 是瀏覽器使用的同源路徑，由 Frontend proxy 轉送至 loopback MinIO，因此不需要將 port 9000 開放至 LAN。
- `.env.example` 只提供 placeholder。請在未納入版本控制的 `.env` 中自行設定實際密碼；修改 template 不會輪替現有 PostgreSQL、Grafana 或 MinIO 帳密。

## 🗺 發展路線 (Roadmap)

### 🟡 Phase 1 & 2: 核心強化與認證 (Active)
- [x] **身分驗證整合**: 已串接 Keycloak（密碼 + 長效 remember-me session）。FIDO2/passkey 曾實作後棄用——WebAuthn RP ID 強制網域，會引入區網 DNS 單點依賴，對內網自用不划算。
- [x] **後端強制驗證 cutover**: 三個後端已逐服務開啟 `AUTH_ENFORCEMENT_ENABLED`，與 gateway 形成雙層防禦。
- [ ] **Python 觀測性優化**: 完善 Python 服務的 Trace 欄位與 Context 傳遞。
- [x] **後端精細化驗證**: `jakarta.validation` 已用於 Java 端 DTO 與 Controller 驗證。
- [x] **MinIO 完整整合**: 圖片上傳已實作。原規劃的 Presigned URL 改為同源 `/minio` proxy（免開放 9000 port）、縮圖改由前端上傳前壓縮取代。

### 🟣 Phase 3: 跨服務業務整合 (Planned)
- [ ] **投資與記帳串接**: 將投資交易產生的現金流與既有記帳規則串接；第一版採同步 API，讓使用者能立即看見成功或失敗。
- [ ] **可追查的業務鏈**: 上述跨服務流程實作時，補齊 Gateway 到後端的 trace propagation，並在 Grafana 建立對應的操作視圖。

### 🔴 Phase 4: 依需求演進 (Planned)
- [x] **API Gateway & Rate Limiting**: Spring Cloud Gateway 統一入口（JWT 驗證 + scope 路由 + bucket4j 限流）。
- [ ] **背景工作與共享快取**: 僅在出現不可接受的等待時間、可靠重試或多實例一致性需求時，再以具體流程評估 queue 或 distributed cache。

---
*Created and maintained as a personal digital life management suite.*

## 📄 授權 (License)

本專案採用 [MIT](LICENSE) 授權。您可以自由使用、修改與分發，但請保留原作者版權聲明。
