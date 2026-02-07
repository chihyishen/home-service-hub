const fs = require('fs');
const path = require('path');

const envPath = path.resolve(__dirname, '../../.env');
const targetPath = path.resolve(__dirname, './src/environments/environment.ts');

let envConfig = {};

if (fs.existsSync(envPath)) {
  const envFile = fs.readFileSync(envPath, 'utf8');
  // Use a more robust split for different OS line endings
  const lines = envFile.split(/\r?\n/);
  lines.forEach(line => {
    // Basic parser: key=value
    const match = line.match(/^\s*([\w.-]+)\s*=\s*(.*)?\s*$/);
    if (match) {
      const key = match[1];
      let value = match[2] || '';
      // Remove quotes if present
      if (value.length > 0 && value.charAt(0) === '"' && value.charAt(value.length - 1) === '"') {
        value = value.substring(1, value.length - 1);
      }
      envConfig[key] = value;
    }
  });
}

const envConfigFile = `export const environment = {
  production: false,
  apiUrl: '${envConfig.FRONTEND_API_URL || '/api'}',
  backendHost: '${envConfig.BACKEND_HOST || 'localhost'}',
  backendPort: '${envConfig.BACKEND_PORT || '1031'}'
};
`;

console.log('Generating environment.ts...');
if (!fs.existsSync(path.dirname(targetPath))) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
}
fs.writeFileSync(targetPath, envConfigFile);
console.log(`Output generated at ${targetPath}`);