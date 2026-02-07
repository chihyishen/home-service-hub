const path = require('path');
const fs = require('fs');

// 嘗試載入環境變數 (與 set-env.js 邏輯一致)
const envPath = path.resolve(__dirname, '../../.env');
let envConfig = {};

if (fs.existsSync(envPath)) {
  const envFile = fs.readFileSync(envPath, 'utf8');
  // 使用更健壯的換行符號切割 (支援不同 OS)
  const lines = envFile.split(/\r?\n/);
  lines.forEach(line => {
    const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
    if (match) {
      envConfig[match[1]] = (match[2] || '').replace(/^["']|["']$/g, '');
    }
  });
}

const BACKEND_HOST = envConfig.BACKEND_HOST;
const BACKEND_PORT = envConfig.BACKEND_PORT;

if (!BACKEND_HOST || !BACKEND_PORT) {
  console.error('\x1b[31m[Proxy Config] Error: BACKEND_HOST or BACKEND_PORT is not defined in .env\x1b[0m');
}

module.exports = {
  "/api": {
    "target": `http://${BACKEND_HOST}:${BACKEND_PORT}`,
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  },
  "/otlp": {
    "target": `http://${BACKEND_HOST}:4318`,
    "pathRewrite": { "^/otlp": "" },
    "secure": false,
    "changeOrigin": true,
    "logLevel": "debug"
  }
};