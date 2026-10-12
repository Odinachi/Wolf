import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // The FastAPI backend (apps/api). Override with WOLF_API_PORT if 8000 is taken.
  const apiPort = loadEnv(mode, '.', 'WOLF_').WOLF_API_PORT || '8000'
  return {
    plugins: [react(), tailwindcss()],
    server: {
      proxy: { '/api': `http://localhost:${apiPort}` },
    },
  }
})
