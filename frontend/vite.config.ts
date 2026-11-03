import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Built files go where Flask serves them from (ocarina/web/dist).
// In `npm run dev` the API and audio are proxied to a running backend.
const backend = process.env.OCARINA_BACKEND ?? 'http://127.0.0.1:5001'

export default defineConfig({
  base: '/ocarina/app/',
  plugins: [react()],
  build: { outDir: '../ocarina/web/dist', emptyOutDir: true },
  server: { proxy: { '/ocarina/api': backend, '/useraudio': backend, '/userimages': backend } },
})
