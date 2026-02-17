module.exports = {
  apps: [
    {
      name: 'item-service',
      cwd: './services/inventory-api',
      script: './gradlew',
      args: ':item-service:bootRun',
      interpreter: 'sh',
      env_file: '../../.env',
    },
    {
      name: 'accounting-service',
      cwd: './services/accounting-service',
      script: './.venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 8000',
      interpreter: 'none',
      env_file: '../../.env',
      env: {
        PYTHONUNBUFFERED: '1',
      },
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
