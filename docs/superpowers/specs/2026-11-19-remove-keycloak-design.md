# 移除 Keycloak、前門改為 nginx 容器 — 設計

日期：2026-11-19

## 意圖與原因

當初導入 Keycloak 有兩個目的：一是要有驗證，二是希望用 Face ID（FIDO／passkey）一刷就登入。passkey 需要網域和受信任的憑證，最後退回「帳號密碼＋拉長 session＋瀏覽器記密碼」。結果登入沒有比較方便，還多了問題：前端為了 keycloak-js 改用自簽 HTTPS，iPhone 加到主畫面的圖示一直出不來。

使用情境：
- 使用者只有屋主本人，主要在家裡內網使用，人在外面時透過 TP-Link 上的 WireGuard 連回內網。
- 系統沒有對外網開放的服務。
- 系統沒有存敏感資料：沒有卡號、沒有密碼，最敏感的是消費紀錄和持股。
- 真正要保護的是 Mac mini 和 PC 本身。威脅來源是內網裡的 IoT 裝置，甚至 TP-Link 路由器本身被入侵。TP-Link 的設備隔離實測有效，但不能當作唯一防線。

結論：對這個情境來說，app 層的登入防不了「網站被當跳板打進 Mac」。真正有效的是讓 Mac 對區網暴露的東西越少、越硬越好。Keycloak 本身就是一個對區網開放的 Java 服務，`ng serve` 則是不該對外服務的開發伺服器。

## 目標

- 完全移除 Keycloak／OIDC／JWT：包括 compose、realm、登入主題、gateway 和三個後端的驗證，以及前端的 keycloak-js。
- 前端改為 production build 出來的靜態檔，由 nginx 容器提供，並把 API 反向代理到 gateway。
- 這個 nginx 是整台 Mac mini 上所有自架服務的唯一區網入口，網址統一是 `http://<ip>/<服務名>/`，方便查找和管理。本次（第一階段）只接 home-service-hub；第二階段把 Grafana、Jellyfin、streamer-dvr 接進來（見文末）。Apple 內建服務（AirPlay、螢幕共享等）不在範圍內，交給系統自己控管。
- 前端改用 HTTP，不再需要自簽憑證；預期 iPhone 主畫面圖示的問題會跟著解決。
- 刪除跟驗證有關的設定、文件和那份未完成的 openspec change。

## 不做的事

- **不加任何形式的登入**，包括 Basic auth 和固定 token。這是屋主的決定，可接受的代價如下：
  - 任何連得到 Mac 的裝置都能完整讀寫這個系統。
  - 「只有 admin 能刪投資組合紀錄」的限制拿掉。
  - Hermes agent「只能動記帳」的限制拿掉。Hermes 目前沒在用。
- 不處理整台 Mac 的網路加固：macOS 防火牆、其他專案對區網開的 port、系統分享服務、Grafana 綁 LAN IP、VPN 終點搬到 Mac。這些另外開一個專案。
- 不把 gateway 和後端搬進容器，它們繼續用 pm2 跑、只綁 `127.0.0.1`。
- 不改 repo 外的 `~/.hermes/.../oidc.py`。它會失效，等哪天要用 Hermes 再改。`~/projects/imessage-bookkeeper` 共用同一支程式，也會失效。

## 反目標（技術上能動但仍算失敗）

- 區網上仍然看得到 8180、8443 或 4200 這幾個 port。
- 有任何後端或 gateway 改成對區網開放。
- nginx 代理了既有路由以外的路徑，或把 gateway 和後端的錯誤細節、版本資訊回傳給瀏覽器。
- 日常使用時因為 gateway rate limit 吃到 429。

## 考慮過的做法

| 做法 | 取捨 | 結果 |
|---|---|---|
| A. 不登入，靠網段隔離和 VPN，前門換成 nginx 容器 | 刪掉的程式碼最多，同時解決登入不便和圖示問題。代價是沒隔離的裝置都能用這個系統 | **選用** |
| B. 在 gateway 用一組 HTTP Basic 密碼，Hermes 用固定 token | 保留一層門檻，但要保留 HTTPS 和自簽憑證；主畫面 web app 對 Basic 帳密框支援不穩 | 不選：資料不敏感，登入防不了跳板攻擊 |
| C. 保留 Keycloak，只在 iPhone 上信任憑證來修圖示 | 改動最少，但複雜度和對區網開放的 Java 服務都還在 | 不選 |

前門的部分也考慮過讓 gateway 直接提供靜態檔。不選的原因是那樣 gateway 這個 JVM 就得對區網開放，nginx 容器的攻擊面比較小，而且還隔著一層容器。

## 已決定的做法

0. **前置條件**：`/minio` 改名 `/images`（含 Flyway `V3__rename_image_url_prefix.sql`）先以獨立 commit 進 main，本工作從那個 commit 開始。下文提到的路徑都是 `/images`。
1. **Keycloak 整套移除。**
   - `docker-compose.yml`：移除 `keycloak` 和 `keycloak-postgres` 兩個 service，以及 `keycloak_postgres_data` volume 的宣告。不主動刪除既有的 docker volume，由屋主自行處理。
   - 刪除 `infra/keycloak/` 下所有受版控的檔案（realm JSON、themes）。gitignore 掉的 certs 留在硬碟上，不在這次處理。
   - 刪除 `scripts/smoke/validate-keycloak-realm.sh`。
2. **Gateway 移除驗證。**
   - 移除 oauth2 resource server 依賴、`security.oidc` 設定和 `AudienceValidator`。
   - `SecurityConfig` 改成只放行既有路由的白名單，其他一律拒絕，保持跟現在相同的路由面。
   - 保留 `RequestBoundaryFilter` 和 rate limit。
3. **三個後端移除驗證。**
   - inventory：`ResourceServerSecurityConfig`、`AuditModeSecurityConfig`、security starter 和 resource-server starter 全部刪除。`AuditModeSecurityConfig` 原本只是關閉驗證時的備案，拿掉 resource server 之後，Spring Security 在 inventory 就沒有任何用途了。
   - Python：刪掉 `shared_lib/auth.py` 和對應測試，移除 `app_factory` 的 `auth_service` 參數、兩個 `main.py` 的呼叫，以及 PyJWT 依賴。
   - `ecosystem.config.js` 和 CI 拿掉 `AUTH_ENFORCEMENT_ENABLED`。
4. **前端。**
   - 刪掉 `src/app/auth/`、`auth.interceptor.ts`、`keycloak-js` 依賴，以及 `app.config.ts`、`app.routes.ts` 裡的相關接線。
   - `set-env.js` 拿掉 oidc 相關欄位。
   - `angular.json` 的 `serve` 拿掉 ssl 設定。`ng serve` 之後只給本機開發用，host 改回預設（localhost）。`proxy.conf.js` 保留給本機開發用。
5. **前門：nginx 容器。**
   - 在 `docker-compose.yml` 新增一個 nginx service，使用非 root 映像，跟其他 service 一樣用 digest 固定版本。
   - 唯讀掛載 `frontend/dist/.../browser`，對區網開放 HTTP。port 由建置者決定，預設建議 80。
   - 網址配置：
     - `/` 是一頁手寫的靜態首頁，列出各服務的連結（第一階段只有 hub）。
     - `/hub/` 是 home-service-hub 前端。Angular 用 `--base-href /hub/` build，SPA 在 `/hub/` 底下用 `try_files` 回到 `index.html`。`manifest.json` 的 `start_url`／`scope` 和主畫面圖示的路徑要跟著調整。
     - API 維持在根路徑，因為只有 hub 用到，前端的 `apiUrl` 也不用改。`location` 只轉送這些路徑到 Mac 上的 gateway（`127.0.0.1:8088`）：`/api/items`、`/api/shopping-list`、`/api/accounting`、`/api/portfolio`、`/images/inventory-items`、`/otlp`。路徑清單跟現在的 `proxy.conf.js` 相同。
     - 設定檔一開始就按服務拆開（例如 `conf.d/hub.conf`），第二階段新增服務時只要加檔案。
     - 其他路徑一律 404。
   - 加上 `server_tokens off`。`client_max_body_size` 至少 15MB，對齊 inventory 的 multipart 上限；portfolio CSV 的上限是 5MB，比它小。
   - 錯誤處理（設計者的決定）：
     - 4xx 回應的 body 原樣透傳，因為前端 `error-logging.interceptor.ts` 會把後端的 `message`、`detail` 顯示成 toast。
     - 只有 5xx 和 gateway 連不上（502、503、504）時，改成回傳通用的錯誤頁，並隱藏 `Server` 等透露版本的 header。
   - 掛載 `frontend/dist` 的上層目錄，不要直接掛 `browser/`。`ng build` 會刪掉並重建輸出資料夾，直接掛的話 nginx 會指到已經不存在的目錄。
   - pm2 移除 `frontend` 這個 app。
   - 前端更新流程改成 `npm run build`，nginx 不用重啟就會吃到新檔案。
   - `ALLOWED_ORIGINS`（`.env` 和 `.env.example`）要加上新的 origin，例如 `http://192.168.0.100`，不然 inventory 的 CORS 會擋掉寫入請求。
6. **`.env.example`** 移除驗證相關的 15 個 key（`OIDC_*`、`KEYCLOAK_*`、`GATEWAY_JWKS_URI`、`IDENTITY_BIND_HOST`）。若新增 nginx 對外 port 的變數，要寫進去。根目錄 `.env` 也同步移除這些 key。
7. **文件。**
   - README（架構圖、啟動方式、入口網址改成 `http://<LAN-IP>/`）、ROADMAP、`docs/security/*`、CLAUDE.md 的請求路徑說明都要更新。
   - `docs/security/keycloak-operations.md` 刪除。
   - `openspec/changes/add-api-gateway-authentication` 用 archive 收掉，註明改採本設計、不再實作。要加 `--skip-specs`，避免驗證相關的 spec 被合併進 `openspec/specs`。
8. **上線收尾。**
   - 停掉 Keycloak 的兩個容器。
   - `pm2 delete frontend` 後執行 `pm2 save`。
   - 重啟 gateway 和三個後端，用 `lsof` 確認 8180、8443、4200 都已經關閉。

## 留給建置者決定

- **nginx 容器怎麼連到 Mac 上只綁 `127.0.0.1` 的 gateway。** 預期 OrbStack 的 `host.docker.internal` 可以連到 Mac 上只聽 localhost 的服務，要實測確認。如果不行，回報給屋主，不要擅自把 gateway 改成對區網開放。
- **Rate limit。** 拿掉 JWT 之後，所有請求的來源都會是 nginx，等於共用同一個 bucket。要用實際儀表板測試；會吃到 429 的話，就提高上限，或改用 nginx 設定、且 gateway 只信任來自 nginx 的 `X-Forwarded-For` 當 key。選最簡單且正確的做法。
- `environment.ts` 的 `production` 旗標是否改由 build configuration 決定。
- 測試：
  - 刪除跟驗證相關的測試。
  - gateway 的 `SecurityConfigTest` 改成驗證白名單（既有路由放行、其他路徑拒絕）。
  - 三個服務和前端的測試套件都要能跑過。

## 驗收

- `lsof -iTCP -sTCP:LISTEN` 在非 loopback 介面上，不再出現 8180、8443、4200，只多出 nginx 的那個 port。
- 從 iPhone 用 `http://192.168.0.100/hub/` 開啟，不用登入就能使用庫存（含照片上傳和顯示）、記帳和投資組合。重新加到主畫面時圖示正確，點開後停留在 `/hub/`。`http://192.168.0.100/` 顯示服務列表。
- 瀏覽器的 trace 仍然能經由 `/otlp` 送進 Tempo。
- Java（inventory、gateway）、Python（accounting、portfolio、shared-lib）、前端的測試全部通過，CI 綠燈。

## 第二階段：其他自架服務接上 nginx（另開計畫）

第一階段上線後再做，沿用同一個 nginx、同樣的 `<ip>/<服務名>/` 規則：

| 網址 | 服務 | 要改的地方 |
|---|---|---|
| `/grafana/` | Grafana（容器，現綁 `127.0.0.1:3000` 與 LAN IP `:3000`） | 設 `GF_SERVER_ROOT_URL` + `GF_SERVER_SERVE_FROM_SUB_PATH`；拿掉 `GRAFANA_VPN_BIND_HOST` 的 LAN 綁定 |
| `/jellyfin/` | Jellyfin（macOS 原生 app，現綁 `*:8096`） | 後台 Networking 設 Base URL `/jellyfin`、綁定位址改 `127.0.0.1`；PC／手機／平板的 Jellyfin app 伺服器網址改成 `http://<ip>/jellyfin`。客戶端只有這三類，沒有 IoT 網段的電視 |
| `/streamer-dvr/` | streamer-dvr（含 `/review` 標註頁，現綁 `*:8787`） | 位於另一個 repo（streamer-rec）；需讓它支援掛在子路徑下並改綁 `127.0.0.1`。舊的 `label_server.py`（`*:8137`，只剩轉址）收掉 |

最後打開 macOS 防火牆，確認區網上只剩 nginx 的 port（加上 Apple 系統服務）。
