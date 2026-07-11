module.exports = {
  apps: [
    {
      name: 'item-service',
      cwd: './services/inventory-api',
      script: './gradlew',
      args: ':item-service:bootRun',
      interpreter: 'sh',
      // .env 由 inventory-api 的 build.gradle.kts 載入（pm2 沒有 env_file 這種欄位）
      env: {
        AUTH_ENFORCEMENT_ENABLED: 'true',
      },
    },
    {
      name: 'accounting-service',
      cwd: './services/accounting-service',
      script: './.venv/bin/uvicorn',
      args: 'app.main:app --host 127.0.0.1 --port 8000',
      interpreter: 'none',
      // .env 由 shared_lib database.py 的 load_dotenv 載入（pm2 沒有 env_file 這種欄位）
      env: {
        PYTHONUNBUFFERED: '1',
        AUTH_ENFORCEMENT_ENABLED: 'true',
      },
    },
    {
      name: 'stock-portfolio-service',
      cwd: './services/stock-portfolio-service',
      script: './.venv/bin/uvicorn',
      args: 'app.main:app --host 127.0.0.1 --port 8001',
      interpreter: 'none',
      // .env 由 shared_lib database.py 的 load_dotenv 載入（pm2 沒有 env_file 這種欄位）
      env: {
        PYTHONUNBUFFERED: '1',
        AUTH_ENFORCEMENT_ENABLED: 'true',
      },
    },
    {
      name: 'gateway-service',
      cwd: './services/gateway-service',
      script: '../inventory-api/gradlew',
      args: '--no-daemon -p . bootRun',
      interpreter: 'sh',
      // .env 由 gateway 的 build.gradle.kts 載入（pm2 沒有 env_file 這種欄位）
    },
    {
      name: 'frontend',
      cwd: './frontend',
      script: 'npm',
      args: 'start',
      env: {
        NODE_ENV: 'development',
      },
    },
  ],
};
