import { defineConfig } from 'vite';

export default defineConfig({
  root: './src',
  build: {
    outDir: '../web/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: './src/main.ts'
      },
      output: {
        entryFileNames: 'js/[name].js',
        chunkFileNames: 'js/[name].js',
        assetFileNames: '[ext]/[name].[ext]'
      }
    }
  },
  server: {
    port: 3000,
    open: false
  }
});