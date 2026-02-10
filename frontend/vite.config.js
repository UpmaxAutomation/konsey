import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild',
    target: 'es2020',
    cssCodeSplit: true,
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom', 'zustand'],
          'vendor-charts': ['recharts'],
          'vendor-syntax': ['react-syntax-highlighter'],
          'vendor-markdown': ['react-markdown', 'remark-gfm'],
          'vendor-reactflow': ['@xyflow/react'],
          'vendor-tiptap': ['@tiptap/react', '@tiptap/starter-kit', '@tiptap/extension-bubble-menu', 'tiptap-markdown'],
        }
      }
    }
  },
})
