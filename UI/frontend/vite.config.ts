import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev the app is served at `/` (http://localhost:5173).
// In a production build we use relative paths so the backend can serve
// the built app from http://127.0.0.1:8000/app/ .
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === 'production' ? './' : '/',
  server: { port: 5173 },
}))
