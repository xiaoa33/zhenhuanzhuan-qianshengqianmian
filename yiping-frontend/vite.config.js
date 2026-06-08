import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// 将 resource/ 目录下的静态资源以 /resource/... 路径暴露给开发服务器
function resourcePlugin() {
  return {
    name: 'vite-plugin-serve-resource',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const rawUrl = req.url || ''
        if (!rawUrl.startsWith('/resource')) return next()

        const decoded = decodeURIComponent(rawUrl.split('?')[0])
        const filePath = path.join(__dirname, decoded)

        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
          const ext = path.extname(filePath).toLowerCase()
          const mimeMap = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.mp3': 'audio/mpeg',
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
          }
          res.setHeader('Content-Type', mimeMap[ext] || 'application/octet-stream')
          fs.createReadStream(filePath).pipe(res)
          return
        }
        next()
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), resourcePlugin()],
  server: {
    port: 5173,
    open: true,
  },
})
