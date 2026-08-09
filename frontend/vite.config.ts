import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true,
        timeout: 600000, // 10 minutes
        configure: (proxy, options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            // Remove problematic headers for large responses
            if (req.url?.includes('/users')) {
              proxyReq.removeHeader('if-none-match');
              proxyReq.removeHeader('if-modified-since');
            }
            if (req.method === 'POST' && req.url?.includes('/upload')) {
              req.setTimeout(600000);
              res.setTimeout(600000);
              proxyReq.removeHeader('content-length');
              proxyReq.setHeader('transfer-encoding', 'chunked');
            }
          });
          proxy.on('proxyRes', (proxyRes, req, res) => {
            // Disable compression for large JSON responses
            if (req.url?.includes('/users') && proxyRes.headers['content-encoding']) {
              delete proxyRes.headers['content-encoding'];
            }
          });
          proxy.on('error', (err, req, res) => {
            console.error('Proxy error:', err.message, 'for', req.url);
            if (!res.headersSent) {
              res.writeHead(500, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ error: 'Proxy error', message: err.message }));
            }
          });
        }
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  }
})