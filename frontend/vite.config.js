import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ['react', 'react-dom'],
  },
  server: {
    port: 5000,
    host: '0.0.0.0',
    allowedHosts: true,
    proxy: {
      '/query': 'http://localhost:8000',
      '/ingest': 'http://localhost:8000',
      '/search': 'http://localhost:8000',
      '/graph': 'http://localhost:8000',
      '/debug': 'http://localhost:8000',
      '/stats': 'http://localhost:8000',
      '/reindex': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
