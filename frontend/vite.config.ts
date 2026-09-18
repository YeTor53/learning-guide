import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 开发期把 /api 转发到后端（同源策略：浏览器只看到 localhost:5173 一个源，Cookie 照常，见架构页 §6）
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
  build: { outDir: 'dist' },
})
