# 修改紀錄 - 2026-02-05 (修復 Grafana Loki 到 Tempo 的 Trace 連結)

## 📋 概述
修正 Grafana Explore 中日誌 (Loki) 無法正確跳轉至鏈路追蹤 (Tempo) 的問題，包含正規表達式修正與 Grafana 10+ 的 Correlation 配置。

## 📅 日期
2026-02-05

## 🔍 遇到了什麼問題？ (Problem Statement)
- **Log Line 連結失效**：Java 日誌中的 `traceId=...` 文字沒有被識別為可點擊連結。
- **Metadata 無連結**：Structured Metadata 中的 `trace_id` 欄位無法跳轉。
- **URL 導向錯誤**：導向地址錯誤地變成了 `http://localhost:3000/traceId`，未帶入實際數值。

## 💡 解決方案 (Solution & Implementation)

### 1. 修正 `derivedFields` 配置
- **Regex 修正**：將匹配規則從 `(?:traceId) (\w+)` 改為 `traceId=(\w+)` 以符合 Logback 輸出。
- **MatcherType**：針對結構化數據新增 `matcherType: "label"`。

### 2. 配置 Correlations (Grafana 10+)
- 定義全域 Correlation，將 Loki 的 `trace_id` 欄位映射至 Tempo 的 `traceId` 查詢。

---

## 📂 關鍵設定檔變動 (Key Code Snippets)

### `infra/config/grafana-config.yaml`
```yaml
datasources:
  - name: Loki
    uid: loki
    jsonData:
      derivedFields:
        - datasourceUid: tempo
          matcherRegex: "traceId=(\w+)"
          name: TraceID
          url: '$${__value.raw}'

correlations:
  - sourceUID: loki
    targetUID: tempo
    config:
      field: "trace_id"
      type: "query"
      target:
        queryType: "traceId"
        query: "$${__value.raw}"
```

---

## ✅ 驗證結果 (Verification)
- [x] Log 文字中的 `traceId=xxx` 變為藍色超連結。
- [x] 點擊 Log 旁邊的 "Trace" 按鈕能準確開啟 Tempo 視圖。

## 🚀 後續行動 (Next Steps)
- 若修改不生效，需執行 `docker compose restart grafana`。
