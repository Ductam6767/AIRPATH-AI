import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

const webRoot = path.dirname(fileURLToPath(import.meta.url))
const demoPack = path.resolve(webRoot, '../data/processed/web_demo')

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'mobile' ? './' : '/',
  resolve: {
    alias: {
      '@demo-pack': demoPack,
    },
  },
  server: {
    port: 5173,
    fs: {
      allow: [path.resolve(webRoot, '..')],
    },
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/demo': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
}))
