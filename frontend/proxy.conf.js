const path = require('path');
const fs = require('fs');

// 載入環境變數
const envPath = path.resolve(__dirname, '../.env');
let envConfig = {};

if (fs.existsSync(envPath)) {
  const envFile = fs.readFileSync(envPath, 'utf8');
  const lines = envFile.split(/\r?\n/);
  lines.forEach(line => {
    const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
    if (match) {
      envConfig[match[1]] = (match[2] || '').replace(/^["']|["']$/g, '');
    }
  });
}

// 嚴格讀取：若缺失必要變數則報錯
const GATEWAY_TARGET = `http://${envConfig.GATEWAY_HOST || '127.0.0.1'}:${envConfig.GATEWAY_PORT || '8088'}`;

module.exports = {
  "/api/items": {
    "target": GATEWAY_TARGET,
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/api/shopping-list": {
    "target": GATEWAY_TARGET,
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/api/accounting": {
    "target": GATEWAY_TARGET,
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/api/portfolio": {
    "target": GATEWAY_TARGET,
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/minio/inventory-items": {
    "target": GATEWAY_TARGET,
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/otlp": {
    // 固定的 Collector HTTP 端點
    "target": GATEWAY_TARGET,
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  }
};
