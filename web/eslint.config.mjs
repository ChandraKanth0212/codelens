import { createRequire } from 'node:module';
const require = createRequire(new URL('../analyzer/package.json', import.meta.url));
const parser = require('@typescript-eslint/parser');
const plugin = require('@typescript-eslint/eslint-plugin');

export default [{
  files: ['src/**/*.{ts,tsx}'],
  languageOptions: { parser, ecmaVersion: 2022, sourceType: 'module', parserOptions: { ecmaFeatures: { jsx: true } } },
  plugins: { '@typescript-eslint': plugin },
  rules: {
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    'no-debugger': 'error', 'no-eval': 'error', 'eqeqeq': 'error',
  },
}];
