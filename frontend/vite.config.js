import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // 5173 belongs to the backend, which serves the built app and the API on
    // one origin. Dev mode runs here and proxies /api across to it, so the
    // frontend can always call a same-origin '/api'.
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': 'http://localhost:5173',
    },
  },
})
