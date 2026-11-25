import { ESLint } from 'eslint';
import parser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import globals from 'globals';

let input = '';
for await (const chunk of process.stdin) {
  input += chunk;
  if (input.length > 250_000) throw new Error('Input limit');
}
const path = process.argv[2];
const ts = /\.tsx?$/.test(path);
const eslint = new ESLint({
  overrideConfigFile: true,
  ignore: false,
  overrideConfig: [{
    files: ['**/*.{js,jsx,ts,tsx,mjs,cjs}'],
    languageOptions: {
      parser,
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.node },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    plugins: { '@typescript-eslint': tsPlugin },
    rules: {
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-debugger': 'warn',
      'eqeqeq': 'warn',
      'no-constant-condition': 'error',
      'no-undef': ts ? 'off' : 'error',
      'no-unused-vars': ts ? 'off' : 'warn',
      '@typescript-eslint/no-unused-vars': ts ? 'warn' : 'off',
    },
  }],
});
const [result] = await eslint.lintText(input, { filePath: `input.${path.split('.').pop()}` });
// Do not emit messages containing source identifiers or literals.
process.stdout.write(JSON.stringify(result.messages.map(({ruleId, line, severity}) => ({ruleId, line, severity}))));
