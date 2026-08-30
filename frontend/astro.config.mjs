import { defineConfig } from 'astro/config';

export default defineConfig({
  server: { port: 3000 },
  vite: { server: { proxy: { '/api': { target: process.env.API_BASE_URL || 'http://localhost:8000', changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, '') } } } }
});
