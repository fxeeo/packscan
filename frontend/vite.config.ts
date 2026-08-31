import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'

export default defineConfig(({ mode }) => {
  const rootDir = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..')
  const env = {
    ...loadEnv(mode, rootDir, ''),
    ...loadEnv(mode, fileURLToPath(new URL('.', import.meta.url)), ''),
  }

  const apiTarget =
    env.VITE_API_PROXY_TARGET ||
    env.PACKSCAN_API_PROXY_TARGET ||
    `http://${env.PACKSCAN_API_HOST || '127.0.0.1'}:${env.PACKSCAN_API_PORT || '8000'}`

  const frontendPort = Number(env.VITE_DEV_PORT || 5173)

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      port: frontendPort,
      // Phone / Cloudflare / localtunnel hostnames (Vite 8 blocks unknown Host headers)
      allowedHosts: true,
      proxy: {
        '/api': apiTarget,
        '/uploads': apiTarget,
        '/reports': apiTarget,
      },
    },
  }
})
