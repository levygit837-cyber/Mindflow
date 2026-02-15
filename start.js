#!/usr/bin/env node

const { spawn } = require('child_process');

console.log('🚀 Iniciando OmniMind...\n');

const app = spawn('npx', ['next', 'dev', '--turbopack'], {
  cwd: __dirname,
  stdio: 'inherit',
  shell: true,
});

app.on('close', (code) => {
  process.exit(code);
});

process.on('SIGINT', () => {
  app.kill('SIGINT');
  process.exit(0);
});

process.on('SIGTERM', () => {
  app.kill('SIGTERM');
  process.exit(0);
});
