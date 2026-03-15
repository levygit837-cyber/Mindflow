import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // http-proxy buffers response by default for non-streaming.
        // Setting selfHandleResponse=false (default) lets it pass through.
        // We force no Content-Length manipulation so SSE chunks flush instantly.
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes, _req) => {
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              proxyRes.headers['x-accel-buffering'] = 'no'
            }
          })
        },
      },
    },
    watch: {
      usePolling: true,
      interval: 1000,
    },
  },
})
