import eslint from '@eslint/js'
import reactPlugin from 'eslint-plugin-react'

export default [
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
  eslint.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: {
        browser: 'readonly',
        document: 'readonly',
        fetch: 'readonly',
        window: 'readonly',
        navigator: 'readonly',
        CustomEvent: 'readonly',
      },
    },
    plugins: { react: reactPlugin },
    rules: {
      'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      'react/jsx-uses-vars': 'error',
    },
  },
]
