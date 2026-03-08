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
const requiredVars = [
  'INVENTORY_ITEM_SERVICE_HOST',
  'INVENTORY_ITEM_SERVICE_PORT',
  'ACCOUNTING_SERVICE_HOST',
  'ACCOUNTING_SERVICE_PORT',
  'STOCK_SERVICE_HOST',
  'STOCK_SERVICE_PORT'
];

requiredVars.forEach(v => {
  if (!envConfig[v]) {
    console.error(`\x1b[31m[Proxy Error] 缺少必要環境變數: ${v}\x1b[0m`);
    process.exit(1);
  }
});

const INVENTORY_TARGET = `http://${envConfig.INVENTORY_ITEM_SERVICE_HOST}:${envConfig.INVENTORY_ITEM_SERVICE_PORT}`;
const ACCOUNTING_TARGET = `http://${envConfig.ACCOUNTING_SERVICE_HOST}:${envConfig.ACCOUNTING_SERVICE_PORT}`;
const STOCK_TARGET = `http://${envConfig.STOCK_SERVICE_HOST}:${envConfig.STOCK_SERVICE_PORT}`;

module.exports = {
  "/api/items": {
    "target": INVENTORY_TARGET,
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/api/shopping-list": {
    "target": INVENTORY_TARGET,
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/api/accounting": {
    "target": ACCOUNTING_TARGET,
    "pathRewrite": { "^/api/accounting": "" },
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/api/portfolio": {
    "target": STOCK_TARGET,
    "pathRewrite": { "^/api/portfolio": "/api/portfolio" },
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/otlp": {
    // 固定的 Collector HTTP 端點
    "target": `http://${envConfig.INFRA_HOST || 'localhost'}:4318`,
    "pathRewrite": { "^/otlp": "" },
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  }
};
