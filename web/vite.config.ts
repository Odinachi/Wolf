import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv, type Plugin } from 'vite'

/** Social networks need absolute image URLs in Open Graph tags; use VITE_SITE_URL when it's set. */
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
  const env = loadEnv(mode, '.', ['WOLF_', 'VITE_'])
  // In development, /api goes to the local backend. Override with WOLF_API_PORT if 8000 is taken.
  const apiPort = env.WOLF_API_PORT || '8000'
  return {
    plugins: [react(), tailwindcss(), absoluteSocialImages(env.VITE_SITE_URL)],
    server: {
      proxy: { '/api': `http://localhost:${apiPort}` },
    },
  }
})
