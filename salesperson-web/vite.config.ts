import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  // Relative base so the bundle also works from the APK's file:// origin.
  base: './',
  server: { port: 5174, host: true },
  build: { outDir: 'dist', target: 'es2020' },
});
