import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv, type Plugin } from 'vite'

/** Social networks need absolute image URLs in Open Graph tags; use SITE_URL when it's set. */
function absoluteSocialImages(siteUrl: string | undefined): Plugin {
  return {
    name: 'wolf-absolute-social-images',
    transformIndexHtml(html) {
      if (!siteUrl) return html
      return html.replace(/content="\/og\.png"/g, `content="${siteUrl.replace(/\/$/, '')}/og.png"`)
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', ['WOLF_', ''])
  // In development, /api goes to the local backend. Override with WOLF_API_PORT if 8000 is taken.
  const apiPort = env.WOLF_API_PORT || '8000'
  return {
    // Only these variables are exposed to browser code (they end up in the public bundle). Listed
    // by full name so a secret such as FIREBASE_SERVICE_ACCOUNT can never leak in by accident.
    envPrefix: ['ALLOW_AUTH', 'API_URL', 'SITE_URL', 'FIREBASE_API_KEY', 'FIREBASE_AUTH_DOMAIN', 'FIREBASE_PROJECT_ID', 'FIREBASE_APP_ID'],
    plugins: [react(), tailwindcss(), absoluteSocialImages(env.SITE_URL)],
    server: {
      // Fixed port: it's the origin the backend allows (WOLF_CORS_ORIGINS). Fail instead of
      // silently moving to another port if 5173 is taken.
      port: 5173,
      strictPort: true,
      proxy: { '/api': `http://localhost:${apiPort}` },
    },
  }
})
