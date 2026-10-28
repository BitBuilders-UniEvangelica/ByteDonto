import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      // Em dev, o frontend chama /api no mesmo endereço em que foi aberto e o
      // Vite repassa para o backend. Assim funciona também pelo celular
      // (npm run dev -- --host) sem esbarrar em CORS nem em "localhost".
      // O Host original é mantido para que os links de imagem gerados pelo
      // backend apontem para o endereço que o navegador usou.
      proxy: {
        '/api': {
          target: env.API_PROXY_TARGET || 'http://localhost:8001',
        },
      },
    },
  }
})
