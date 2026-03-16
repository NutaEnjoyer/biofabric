import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3100,
    proxy: {
      '/api/marketing': {
        target: 'http://localhost:8101',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/marketing/, '/v1/marketing'),
      },
      '/api/quarantine': {
        target: 'http://localhost:8102',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/quarantine/, '/v1/quarantine'),
      },
      '/api/procurement': {
        target: 'http://localhost:8103',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/procurement/, ''),
      },
      '/api': {
        target: 'http://localhost:8100',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/v1/legal'),
      },
    },
  },
})
