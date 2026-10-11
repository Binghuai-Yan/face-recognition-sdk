const { defineConfig } = require('vitest/config')
const vue = require('@vitejs/plugin-vue')
const path = require('path')
module.exports = defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  test: {
    environment: 'jsdom', globals: true, include: ['tests/**/*.test.js'],
    environmentOptions: { jsdom: { url: process.env.FACESDK_WEB_URL || 'http://localhost/' } }
  }
})
