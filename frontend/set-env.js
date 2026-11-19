const fs = require('fs');
const path = require('path');

const envPath = path.resolve(__dirname, '../.env');
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

// 嚴格校驗
const required = ['FRONTEND_API_URL'];

required.forEach(v => {
  if (!envConfig[v]) {
    console.error(`\x1b[31m[Env Error] 缺少必要環境變數: ${v}\x1b[0m`);
    process.exit(1);
  }
});

const envConfigFile = `export const environment = {
  production: false,
  apiUrl: '${envConfig.FRONTEND_API_URL}'
};
`;

console.log('Generating environment.ts...');
if (!fs.existsSync(path.dirname(targetPath))) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
}
fs.writeFileSync(targetPath, envConfigFile);
