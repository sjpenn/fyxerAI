/**
 * Test setup file for Vitest
 * Configures global test environment and mocks
 */

import { beforeEach, afterEach, vi } from 'vitest'
import '@testing-library/jest-dom'

// Mock WebSocket for testing
global.WebSocket = vi.fn(() => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  send: vi.fn(),
  close: vi.fn(),
  readyState: WebSocket.OPEN,
  CONNECTING: 0,
  OPEN: 1,
  CLOSING: 2,
  CLOSED: 3
}))

// Mock Notification API
global.Notification = vi.fn(() => ({
  close: vi.fn()
}))
global.Notification.requestPermission = vi.fn(() => Promise.resolve('granted'))
global.Notification.permission = 'granted'

// Mock Audio API
global.Audio = vi.fn(() => ({
  play: vi.fn(() => Promise.resolve()),
  pause: vi.fn(),
  load: vi.fn(),
  volume: 0.3
}))

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
global.localStorage = localStorageMock

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
global.sessionStorage = sessionStorageMock

// Mock fetch API
global.fetch = vi.fn()

// Mock CSRF token
global.document.querySelector = vi.fn((selector) => {
  if (selector === '[name=csrfmiddlewaretoken]') {
    return { value: 'test-csrf-token' }
  }
  return null
})

// Mock Alpine.js
global.Alpine = {
  store: vi.fn(() => ({
    realtime: {
      syncConnected: false,
      notificationsConnected: false,
      syncStatus: {
        active_accounts: 0,
        total_accounts: 0,
        last_sync: null,
        is_syncing: false
      },
      unreadCount: 0,
      recentNotifications: [],
      recentEmails: [],
      markEmailRead: vi.fn(),
      startSync: vi.fn(),
      addNotification: vi.fn(),
      removeNotification: vi.fn()
    }
  })),
  data: vi.fn(),
  directive: vi.fn(),
  magic: vi.fn(),
  start: vi.fn()
}

// Mock HTMX
global.htmx = {
  config: {
    globalViewTransitions: true,
    defaultSwapStyle: 'innerHTML',
    defaultSwapDelay: 0,
    defaultSettleDelay: 20
  },
  process: vi.fn(),
  swap: vi.fn(),
  trigger: vi.fn()
}

// Mock Chrome Extension API
global.chrome = {
  runtime: {
    sendMessage: vi.fn(),
    onMessage: {
      addListener: vi.fn(),
      removeListener: vi.fn()
    },
    getURL: vi.fn((path) => `chrome-extension://test/${path}`),
    id: 'test-extension-id'
  },
  storage: {
    sync: {
      get: vi.fn(() => Promise.resolve({})),
      set: vi.fn(() => Promise.resolve()),
      remove: vi.fn(() => Promise.resolve())
    },
    local: {
      get: vi.fn(() => Promise.resolve({})),
      set: vi.fn(() => Promise.resolve()),
      remove: vi.fn(() => Promise.resolve())
    }
  },
  tabs: {
    query: vi.fn(() => Promise.resolve([])),
    sendMessage: vi.fn(() => Promise.resolve())
  },
  contextMenus: {
    create: vi.fn(),
    remove: vi.fn(),
    removeAll: vi.fn()
  }
}

// Mock TrustedTypes for CSP compliance
global.trustedTypes = {
  createPolicy: vi.fn((name, rules) => ({
    createHTML: rules?.createHTML || vi.fn(str => str),
    createScript: rules?.createScript || vi.fn(str => str),
    createScriptURL: rules?.createScriptURL || vi.fn(str => str)
  }))
}

// Setup and teardown
beforeEach(() => {
  // Reset all mocks before each test
  vi.clearAllMocks()
  
  // Reset DOM
  document.body.innerHTML = ''
  document.head.innerHTML = ''
  
  // Reset localStorage
  localStorageMock.getItem.mockReturnValue(null)
  localStorageMock.setItem.mockImplementation(() => {})
  
  // Reset fetch
  fetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve('')
  })
})

afterEach(() => {
  // Cleanup after each test
  vi.restoreAllMocks()
})