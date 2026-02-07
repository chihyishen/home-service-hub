# 修改紀錄 - 2026-02-07 (可觀測性與環境變數同步優化)

## 📋 概述
今日完成了全系統的環境變數同步機制，並實作了 Angular 前端到 Java 後端的全鏈路追蹤 (End-to-End Distributed Tracing)，解決了遠端開發環境下的網路連線限制與安全性問題。

## 📅 日期
2026-02-07

## 🔍 遇到了什麼問題？ (Problem Statement)
- **環境變數散亂**：敏感資訊（IP/Port）散佈在各 JSON/YAML 中，且易誤交至 Git。
- **遠端連線失敗**：PC 瀏覽器連不到 Server 的 OTel Collector (Connection Refused)。
- **路徑拼接錯誤**：使用 Proxy 轉發 OTel 數據時，因 SDK 自動補齊路徑導致 404 (Not Found)。
- **編譯報錯**：Angular 21 (ESM) 下 OTel SDK 2.x 的 `Resource` 型別衝突。

## 💡 解決方案 (Solution & Implementation)

### 1. 建立「單一配置來源」機制
- **Backend**: 實作 `DotEnvLoader` 在啟動前自動載入 `.env`。
- **Frontend**: 透過 `set-env.js` 自動生成 `environment.ts` 並動態更新 `angular.json`。

### 2. 實作「無痕 Proxy 轉發」方案
- 在 `proxy.conf.js` 新增 `/otlp` 映射，搭配 `pathRewrite` 解決路徑重複問題。
- 前端 `tracing.ts` 改用相對路徑，讓請求透過 4200 埠轉發，避開 CORS 與網路隔離。

### 3. 優化 OTel SDK 2.x 整合
- 改用 `resourceFromAttributes` 工廠函數建立資源對象。
- 實作 `errorLoggingInterceptor`，在 API 報錯時自動於 Console 印出 TraceID。

---

## 📂 關鍵設定檔變動 (Key Code Snippets)

### `proxy.conf.js` (Proxy 轉發 OTel)
```javascript
  "/otlp": {
    "target": `http://${BACKEND_HOST}:4318`,
    "pathRewrite": { "^/otlp": "" },
    "changeOrigin": true
  }
```

### `tracing.ts` (前端 OTel 初始化)
```typescript
  const exporter = new OTLPTraceExporter({ url: `/otlp/v1/traces` });
  const provider = new WebTracerProvider({
    resource: resourceFromAttributes({ [ATTR_SERVICE_NAME]: 'inventory-ui' }),
    spanProcessors: [new BatchSpanProcessor(exporter)]
  });
```

---

## ✅ 驗證結果 (Verification)
- [x] 成功透過 PC 瀏覽器發送 Traces 至 Server 端 Collector。
- [x] API 報錯時，Console 正確顯示精美的 TraceID 區塊。
- [x] `git diff` 顯示代碼中已無任何私人 IP/Port。

## 🚀 後續行動 (Next Steps)
- 定期確認 `.env` 變數是否完整。
- 未來可擴充前端性能指標 (FCP/LCP) 的蒐集。
