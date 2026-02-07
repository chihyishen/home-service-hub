# 修改紀錄 - 2026-02-05 (Spring Boot 4.0.1 觀測性架構遷移)

## 📋 概述
將 Home Inventory System 的 Java 監控架構升級為「全原生 OTLP 協議」，並整合 Loki 3.0 與 Tempo 2.x。

## 📅 日期
2026-02-05

## 🔍 遇到了什麼問題？ (Problem Statement)
- **依賴衝突**：手動標註版本號導致 Spring Boot BOM 失效。
- **404 導出錯誤**：Java 端 OTLP Exporter 未補齊 `/v1/traces` 導致連線失敗。
- **日誌丟失**：OTel Logback Appender 未正確初始化，Collector 沒收到 Logs。
- **Loki 存儲限制**：舊版 Loki 不支援 OTLP Protobuf 格式。

## 💡 解決方案 (Solution & Implementation)

### 1. 依賴管理優化
- 移除子模組版本號，統一由 Root Gradle 搭配 Spring Boot BOM 管理。
- 加入 `opentelemetry-api-incubator` 解決 Logback 擴展屬性缺失問題。

### 2. OTLP 統一化
- 棄用舊的 HTTP JSON 導出，改用 `opentelemetry-logback-appender` 走 OTLP 協議。
- 在 `LoggingConfig.java` 中使用 `@PostConstruct` 手動安裝 `OpenTelemetryAppender`。

### 3. 基礎設施升級
- 升級 Loki 至 3.0 並切換至 `tsdb` 引擎以支援 OTLP 資料格式。

---

## 📂 關鍵設定檔變動 (Key Code Snippets)

### `LoggingConfig.java`
```java
@PostConstruct
public void setupLogbackAppender() {
    OpenTelemetryAppender.install(openTelemetry); // 手動交接初始化
}
```

### `otel-collector-config.yaml`
```yaml
exporters:
  otlp_http/loki:
    endpoint: "http://loki:3100/otlp" # Loki 3.0 OTLP 接收點
```

---

## ✅ 驗證結果 (Verification)
- [x] Logs, Traces, Metrics 統一透過 OTLP 協定傳輸。
- [x] Java 服務啟動不再噴出 OTel Exporter 404 錯誤。

## 🚀 後續行動 (Next Steps)
- 監控 Loki 的 TSDB 存儲佔用情況。
