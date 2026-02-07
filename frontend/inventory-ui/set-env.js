const fs = require('fs');
const path = require('path');

const envPath = path.resolve(__dirname, '../../.env');
const targetPath = path.resolve(__dirname, './src/environments/environment.ts');

let envConfig = {};

if (fs.existsSync(envPath)) {
  const envFile = fs.readFileSync(envPath, 'utf8');
  const lines = envFile.split(/\r?\n/);
  lines.forEach(line => {
    const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
    if (match) {
      const key = match[1];
      let value = match[2] || '';
      if (value.length > 0 && value.charAt(0) === '"' && value.charAt(value.length - 1) === '"') {
        value = value.substring(1, value.length - 1);
      }
      envConfig[key] = value;
    }
  });
}

// 1. 生成 environment.ts (已在 .gitignore 中)
const envConfigFile = `export const environment = {
  production: false,
  apiUrl: '${envConfig.FRONTEND_API_URL || '/api'}',
  backendHost: '${envConfig.BACKEND_HOST || 'localhost'}',
  backendPort: '${envConfig.BACKEND_PORT || '1031'}',
  otelEndpoint: '${envConfig.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318'}'
};
`;

console.log('Generating environment.ts...');
if (!fs.existsSync(path.dirname(targetPath))) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
}
fs.writeFileSync(targetPath, envConfigFile);

// 2. 更新 angular.json 中的 allowedHosts
const angularJsonPath = path.resolve(__dirname, './angular.json');
if (fs.existsSync(angularJsonPath) && envConfig.ALLOWED_HOSTS) {
  console.log('Updating angular.json allowedHosts for dev server...');
  const angularJson = JSON.parse(fs.readFileSync(angularJsonPath, 'utf8'));
  const hosts = envConfig.ALLOWED_HOSTS.split(',').map(h => h.trim()).filter(h => h);
  
  if (angularJson.projects && angularJson.projects['inventory-ui'] && 
      angularJson.projects['inventory-ui'].architect && 
      angularJson.projects['inventory-ui'].architect.serve && 
      angularJson.projects['inventory-ui'].architect.serve.options) {
    
    angularJson.projects['inventory-ui'].architect.serve.options.allowedHosts = hosts;
    fs.writeFileSync(angularJsonPath, JSON.stringify(angularJson, null, 2) + '\n');
    console.log('angular.json updated successfully.');
  }
}