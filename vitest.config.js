import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.js'],
    include: ['tests/unit/**/*.test.js', 'tests/integration/**/*.test.js'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'tests/',
        'static/js/alpine.min.js',
        'static/js/htmx.min.js'
      ],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80
        }
      }
    },
    testTimeout: 10000,
    hookTimeout: 10000
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './static'),
      '@js': path.resolve(__dirname, './static/js'),
      '@css': path.resolve(__dirname, './static/css'),
      '@tests': path.resolve(__dirname, './tests')
    }
  },
  define: {
    global: 'globalThis'
  },
  server: {
    deps: {
      inline: ['@testing-library/jest-dom']
    }
  }
})