import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// One self-contained bundle (app.js + app.css) that the Python renderer inlines into the page, next to
// the fonts and the data: the dashboard still fetches nothing at runtime.
export default defineConfig({
  plugins: [react()],
  define: { 'process.env.NODE_ENV': '"production"' },
  build: {
    outDir: '../src/statementlens/adapters/render/web_dist',
    emptyOutDir: true,
    cssCodeSplit: false,
    assetsInlineLimit: 100_000_000,
    sourcemap: false,
    rollupOptions: {
      input: 'src/main.jsx',
      output: { format: 'iife', entryFileNames: 'app.js', assetFileNames: 'app.[ext]', inlineDynamicImports: true },
    },
  },
});
