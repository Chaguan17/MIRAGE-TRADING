import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      devOptions: {
        enabled: true // Esto nos permite probar la PWA en desarrollo
      },
      manifest: {
        name: 'Mirage Trading Bot',
        short_name: 'Mirage',
        description: 'Dashboard del bot de trading algorítmico',
        theme_color: '#ffffff',
        icons: [
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      }
    })
  ]
})