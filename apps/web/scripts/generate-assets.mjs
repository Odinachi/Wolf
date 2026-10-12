// Renders the favicon PNGs and the Open Graph image from SVG sources.
// Run with: npm run assets -w @wolf/web
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import sharp from 'sharp'

const pub = (p) => fileURLToPath(new URL(`../public/${p}`, import.meta.url))
const logo = readFileSync(pub('logo.svg'))

for (const [file, size] of [['favicon-32.png', 32], ['apple-touch-icon.png', 180], ['icon-192.png', 192], ['icon-512.png', 512]]) {
  await sharp(logo, { density: 600 }).resize(size, size).png().toFile(pub(file))
}

// The logo's paths, reused inside the OG image.
const mark = logo.toString().replace(/^[\s\S]*?<rect[^>]*\/>/, '').replace(/<\/svg>\s*$/, '')

const phone = (x, y, rotate, accent, title) => `
  <g transform="translate(${x} ${y}) rotate(${rotate})">
    <rect width="230" height="470" rx="36" fill="#0B0B12"/>
    <rect x="9" y="9" width="212" height="452" rx="28" fill="#FFFFFF"/>
    <rect x="85" y="18" width="60" height="16" rx="8" fill="#0B0B12"/>
    <text x="28" y="78" font-family="Helvetica, Arial, sans-serif" font-size="20" font-weight="700" fill="#18181B">${title}</text>
    <rect x="28" y="96" width="174" height="110" rx="16" fill="${accent}" fill-opacity="0.18"/>
    <circle cx="62" cy="151" r="20" fill="${accent}"/>
    <rect x="96" y="138" width="86" height="10" rx="5" fill="${accent}" fill-opacity="0.6"/>
    <rect x="96" y="156" width="60" height="8" rx="4" fill="#D4D4D8"/>
    <rect x="28" y="224" width="80" height="80" rx="14" fill="#F4F4F5"/>
    <rect x="122" y="224" width="80" height="80" rx="14" fill="#F4F4F5"/>
    <rect x="28" y="318" width="174" height="10" rx="5" fill="#E4E4E7"/>
    <rect x="28" y="336" width="120" height="10" rx="5" fill="#E4E4E7"/>
    <rect x="28" y="386" width="174" height="44" rx="14" fill="${accent}"/>
  </g>`

const og = `
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="wolf-bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#4F46E5"/><stop offset="0.55" stop-color="#9333EA"/><stop offset="1" stop-color="#EC4899"/>
    </linearGradient>
    <radialGradient id="g1" cx="0.2" cy="1" r="0.8"><stop offset="0" stop-color="#6366F1" stop-opacity="0.55"/><stop offset="1" stop-color="#6366F1" stop-opacity="0"/></radialGradient>
    <radialGradient id="g2" cx="0.6" cy="1.05" r="0.7"><stop offset="0" stop-color="#EC4899" stop-opacity="0.5"/><stop offset="1" stop-color="#EC4899" stop-opacity="0"/></radialGradient>
    <radialGradient id="g3" cx="0.95" cy="0.9" r="0.6"><stop offset="0" stop-color="#F97316" stop-opacity="0.45"/><stop offset="1" stop-color="#F97316" stop-opacity="0"/></radialGradient>
    <linearGradient id="wave" x1="0" x2="1"><stop offset="0" stop-color="#6366F1"/><stop offset="0.5" stop-color="#D946EF"/><stop offset="1" stop-color="#FB923C"/></linearGradient>
  </defs>
  <rect width="1200" height="630" fill="#FCFCFD"/>
  <rect width="1200" height="630" fill="url(#g1)"/>
  <rect width="1200" height="630" fill="url(#g2)"/>
  <rect width="1200" height="630" fill="url(#g3)"/>
  <path d="M0 520 C 200 460, 400 580, 600 520 S 1000 460, 1200 520 L1200 630 L0 630 Z" fill="url(#wave)" fill-opacity="0.35"/>
  <path d="M0 560 C 250 510, 450 610, 700 560 S 1050 520, 1200 560 L1200 630 L0 630 Z" fill="url(#wave)" fill-opacity="0.5"/>
  <g transform="translate(80 92) scale(1.25)">
    <rect width="64" height="64" rx="16" fill="url(#wolf-bg)"/>${mark}
  </g>
  <text x="182" y="146" font-family="Helvetica, Arial, sans-serif" font-size="48" font-weight="700" fill="#09090B" letter-spacing="-1">Wolf</text>
  <text x="80" y="276" font-family="Helvetica, Arial, sans-serif" font-size="66" font-weight="700" fill="#09090B" letter-spacing="-2.5">Build mobile apps</text>
  <text x="80" y="352" font-family="Helvetica, Arial, sans-serif" font-size="66" font-weight="700" fill="#09090B" letter-spacing="-2.5">by chatting with AI</text>
  <text x="80" y="420" font-family="Helvetica, Arial, sans-serif" font-size="28" fill="#52525B">Describe it. Edit it like a design. Ship it in Flutter.</text>
  ${phone(760, 120, -8, '#7C3AED', 'Plant Pal')}
  ${phone(930, 90, 7, '#EC4899', 'Fit Coach')}
</svg>`
await sharp(Buffer.from(og)).png().toFile(pub('og.png'))
console.log('Generated favicons and og.png')
