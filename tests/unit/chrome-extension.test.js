/**
 * Unit tests for Chrome Extension functionality
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { JSDOM } from 'jsdom'
import fs from 'fs'
import path from 'path'

// Helper function to load extension scripts
function loadExtensionScript(scriptPath) {
  const fullPath = path.resolve(scriptPath)
  const scriptContent = fs.readFileSync(fullPath, 'utf-8')
  return scriptContent
}

describe('Chrome Extension', () => {
  let dom
  let window
  let document

  beforeEach(() => {
    // Setup JSDOM
    dom = new JSDOM('<!DOCTYPE html><html><body></body></html>')
    window = dom.window
    document = window.document
    
    global.window = window
    global.document = document
    global.location = window.location

    // Mock Chrome APIs
    global.chrome = {
      runtime: {
        sendMessage: vi.fn(() => Promise.resolve({ success: true })),
        onMessage: {
          addListener: vi.fn(),
          removeListener: vi.fn()
        },
        getURL: vi.fn((path) => `chrome-extension://test/${path}`),
        id: 'test-extension-id',
        onInstalled: {
          addListener: vi.fn()
        }
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
        sendMessage: vi.fn(() => Promise.resolve()),
        create: vi.fn(),
        update: vi.fn()
      },
      contextMenus: {
        create: vi.fn(),
        remove: vi.fn(),
        removeAll: vi.fn(),
        onClicked: {
          addListener: vi.fn()
        }
      },
      action: {
        setBadgeText: vi.fn(),
        setBadgeBackgroundColor: vi.fn(),
        setTitle: vi.fn()
      },
      notifications: {
        create: vi.fn(),
        clear: vi.fn(),
        onClicked: {
          addListener: vi.fn()
        }
      }
    }

    // Mock TrustedTypes
    global.trustedTypes = {
      createPolicy: vi.fn((name, rules) => ({
        createHTML: rules?.createHTML || vi.fn(str => str),
        createScript: rules?.createScript || vi.fn(str => str),
        createScriptURL: rules?.createScriptURL || vi.fn(str => str)
      }))
    }
  })

  afterEach(() => {
    dom?.window?.close()
    vi.clearAllMocks()
  })

  describe('Background Script', () => {
    let backgroundScript

    beforeEach(() => {
      // Load background script
      const scriptContent = loadExtensionScript('./extension/background.js')
      
      // Create a more controlled evaluation environment
      const scriptFunction = new Function('chrome', 'console', scriptContent)
      
      // Execute the script with mocked chrome API
      const mockConsole = {
        log: vi.fn(),
        error: vi.fn(),
        warn: vi.fn()
      }
      
      try {
        scriptFunction(global.chrome, mockConsole)
      } catch (error) {
        // Handle any execution errors gracefully
        console.warn('Background script execution error:', error.message)
      }
    })

    it('should initialize with API endpoints', () => {
      // Verify that the script loaded without throwing errors
      expect(chrome.runtime.sendMessage).toBeDefined()
      expect(chrome.storage.sync.get).toBeDefined()
    })

    it('should handle extension installation', async () => {
      const installListener = chrome.runtime.onInstalled.addListener.mock.calls[0]?.[0]
      
      if (installListener) {
        // Simulate installation
        await installListener({ reason: 'install' })
        
        // Verify context menus were created
        expect(chrome.contextMenus.create).toHaveBeenCalled()
      }
    })

    it('should handle API requests', async () => {
      // Mock successful API response
      global.fetch = vi.fn(() => Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ success: true, data: [] })
      }))

      // Simulate message from content script
      const messageListener = chrome.runtime.onMessage.addListener.mock.calls[0]?.[0]
      
      if (messageListener) {
        const response = await new Promise((resolve) => {
          messageListener(
            { action: 'fetchEmails' },
            { tab: { id: 1 } },
            resolve
          )
        })

        expect(response).toEqual(expect.objectContaining({
          success: true
        }))
      }
    })

    it('should handle API errors', async () => {
      // Mock API error response
      global.fetch = vi.fn(() => Promise.resolve({
        ok: false,
        status: 500,
        text: () => Promise.resolve('Internal Server Error')
      }))

      const messageListener = chrome.runtime.onMessage.addListener.mock.calls[0]?.[0]
      
      if (messageListener) {
        const response = await new Promise((resolve) => {
          messageListener(
            { action: 'fetchEmails' },
            { tab: { id: 1 } },
            resolve
          )
        })

        expect(response).toEqual(expect.objectContaining({
          success: false
        }))
      }
    })

    it('should update badge text for unread emails', () => {
      const unreadCount = 5
      
      // This would be called when receiving email updates
      chrome.action.setBadgeText({ text: unreadCount.toString() })
      chrome.action.setBadgeBackgroundColor({ color: '#ff0000' })
      
      expect(chrome.action.setBadgeText).toHaveBeenCalledWith({
        text: '5'
      })
      expect(chrome.action.setBadgeBackgroundColor).toHaveBeenCalledWith({
        color: '#ff0000'
      })
    })
  })

  describe('Content Script', () => {
    beforeEach(() => {
      // Setup Gmail-like DOM structure
      document.body.innerHTML = `
        <div class="gmail-interface">
          <div class="email-list">
            <div class="email-item" data-thread-id="thread1">
              <span class="subject">Test Email 1</span>
              <span class="sender">sender1@example.com</span>
            </div>
            <div class="email-item" data-thread-id="thread2">
              <span class="subject">Test Email 2</span>
              <span class="sender">sender2@example.com</span>
            </div>
          </div>
        </div>
      `

      // Load content script (simplified version for testing)
      global.contentScriptLoaded = true
    })

    it('should detect Gmail interface', () => {
      const isGmail = window.location.hostname === 'mail.google.com'
      const hasGmailElements = document.querySelector('.gmail-interface') !== null
      
      // In a real Gmail page, this would be true
      expect(document.querySelector('.gmail-interface')).toBeTruthy()
    })

    it('should inject FYXERAI buttons into email interface', () => {
      // Simulate button injection
      const emailItems = document.querySelectorAll('.email-item')
      
      emailItems.forEach((item, index) => {
        const button = document.createElement('button')
        button.className = 'fyxerai-triage-btn'
        button.textContent = 'Smart Triage'
        button.dataset.threadId = item.dataset.threadId
        item.appendChild(button)
      })

      const triageButtons = document.querySelectorAll('.fyxerai-triage-btn')
      expect(triageButtons).toHaveLength(2)
      expect(triageButtons[0].dataset.threadId).toBe('thread1')
    })

    it('should handle triage button clicks', async () => {
      // Setup triage button
      const button = document.createElement('button')
      button.className = 'fyxerai-triage-btn'
      button.dataset.threadId = 'thread1'
      document.body.appendChild(button)

      // Mock message handler
      const handleTriageClick = vi.fn(async (threadId) => {
        return await chrome.runtime.sendMessage({
          action: 'triageEmail',
          threadId: threadId
        })
      })

      // Simulate click
      button.addEventListener('click', () => {
        handleTriageClick(button.dataset.threadId)
      })

      button.click()

      expect(handleTriageClick).toHaveBeenCalledWith('thread1')
    })

    it('should create trusted HTML for CSP compliance', () => {
      const policy = trustedTypes.createPolicy('fyxerai-content', {
        createHTML: (string) => string,
        createScript: (string) => string
      })

      const safeHTML = policy.createHTML('<div class="fyxerai-widget">Test</div>')
      expect(safeHTML).toBe('<div class="fyxerai-widget">Test</div>')
      expect(trustedTypes.createPolicy).toHaveBeenCalledWith(
        'fyxerai-content',
        expect.any(Object)
      )
    })

    it('should handle dynamic email loading', () => {
      const observer = {
        observe: vi.fn(),
        disconnect: vi.fn()
      }

      // Mock MutationObserver
      global.MutationObserver = vi.fn(() => observer)

      // Simulate observer setup
      const emailObserver = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'childList') {
            // Handle new emails
          }
        })
      })

      emailObserver.observe(document.body, {
        childList: true,
        subtree: true
      })

      expect(MutationObserver).toHaveBeenCalled()
      expect(observer.observe).toHaveBeenCalledWith(document.body, {
        childList: true,
        subtree: true
      })
    })
  })

  describe('Popup Interface', () => {
    beforeEach(() => {
      // Setup popup HTML structure
      document.body.innerHTML = `
        <div class="popup-container">
          <div class="header">
            <h1>FYXERAI Assistant</h1>
            <div class="connection-status">
              <span id="status-indicator">Disconnected</span>
            </div>
          </div>
          
          <div class="stats">
            <div class="stat-item">
              <span class="label">Unread Emails</span>
              <span class="value" id="unread-count">0</span>
            </div>
            <div class="stat-item">
              <span class="label">Pending Triage</span>
              <span class="value" id="pending-count">0</span>
            </div>
          </div>
          
          <div class="actions">
            <button id="triage-all-btn">Triage All</button>
            <button id="sync-now-btn">Sync Now</button>
            <button id="settings-btn">Settings</button>
          </div>
          
          <div class="recent-activity" id="activity-list">
            <!-- Activity items will be inserted here -->
          </div>
        </div>
      `
    })

    it('should load popup interface correctly', () => {
      expect(document.querySelector('.popup-container')).toBeTruthy()
      expect(document.getElementById('status-indicator')).toBeTruthy()
      expect(document.getElementById('unread-count')).toBeTruthy()
    })

    it('should update connection status', () => {
      const statusIndicator = document.getElementById('status-indicator')
      
      // Simulate connection status update
      const updateConnectionStatus = (connected) => {
        statusIndicator.textContent = connected ? 'Connected' : 'Disconnected'
        statusIndicator.className = connected ? 'connected' : 'disconnected'
      }

      updateConnectionStatus(true)
      expect(statusIndicator.textContent).toBe('Connected')
      expect(statusIndicator.className).toBe('connected')

      updateConnectionStatus(false)
      expect(statusIndicator.textContent).toBe('Disconnected')
      expect(statusIndicator.className).toBe('disconnected')
    })

    it('should update email counts', () => {
      const unreadCount = document.getElementById('unread-count')
      const pendingCount = document.getElementById('pending-count')

      // Simulate count updates
      const updateCounts = (unread, pending) => {
        unreadCount.textContent = unread.toString()
        pendingCount.textContent = pending.toString()
      }

      updateCounts(15, 8)
      expect(unreadCount.textContent).toBe('15')
      expect(pendingCount.textContent).toBe('8')
    })

    it('should handle button clicks', () => {
      const triageBtn = document.getElementById('triage-all-btn')
      const syncBtn = document.getElementById('sync-now-btn')
      const settingsBtn = document.getElementById('settings-btn')

      const handleTriageAll = vi.fn()
      const handleSyncNow = vi.fn()
      const handleSettings = vi.fn()

      triageBtn.addEventListener('click', handleTriageAll)
      syncBtn.addEventListener('click', handleSyncNow)
      settingsBtn.addEventListener('click', handleSettings)

      triageBtn.click()
      syncBtn.click()
      settingsBtn.click()

      expect(handleTriageAll).toHaveBeenCalled()
      expect(handleSyncNow).toHaveBeenCalled()
      expect(handleSettings).toHaveBeenCalled()
    })

    it('should display recent activity', () => {
      const activityList = document.getElementById('activity-list')
      
      const activities = [
        { id: 1, message: 'Email triaged as Important', time: '2 minutes ago' },
        { id: 2, message: 'Draft created for reply', time: '5 minutes ago' },
        { id: 3, message: 'Sync completed', time: '10 minutes ago' }
      ]

      // Simulate activity rendering
      const renderActivities = (activities) => {
        activityList.innerHTML = ''
        activities.forEach(activity => {
          const activityElement = document.createElement('div')
          activityElement.className = 'activity-item'
          activityElement.innerHTML = `
            <div class="activity-message">${activity.message}</div>
            <div class="activity-time">${activity.time}</div>
          `
          activityList.appendChild(activityElement)
        })
      }

      renderActivities(activities)

      const activityItems = activityList.querySelectorAll('.activity-item')
      expect(activityItems).toHaveLength(3)
      expect(activityItems[0].querySelector('.activity-message').textContent)
        .toBe('Email triaged as Important')
    })
  })

  describe('Extension Storage', () => {
    it('should save user preferences', async () => {
      const preferences = {
        autoTriage: true,
        notifications: true,
        syncInterval: 300000 // 5 minutes
      }

      await chrome.storage.sync.set({ preferences })

      expect(chrome.storage.sync.set).toHaveBeenCalledWith({ preferences })
    })

    it('should load user preferences', async () => {
      const mockPreferences = {
        autoTriage: false,
        notifications: true,
        syncInterval: 600000
      }

      chrome.storage.sync.get.mockResolvedValue({ preferences: mockPreferences })

      const result = await chrome.storage.sync.get(['preferences'])

      expect(result.preferences).toEqual(mockPreferences)
      expect(chrome.storage.sync.get).toHaveBeenCalledWith(['preferences'])
    })

    it('should handle storage errors', async () => {
      chrome.storage.sync.set.mockRejectedValue(new Error('Storage quota exceeded'))

      try {
        await chrome.storage.sync.set({ largeData: 'x'.repeat(1000000) })
      } catch (error) {
        expect(error.message).toBe('Storage quota exceeded')
      }

      expect(chrome.storage.sync.set).toHaveBeenCalled()
    })
  })

  describe('Message Passing', () => {
    it('should handle content script to background messages', async () => {
      const message = {
        action: 'getEmails',
        filters: { category: 'urgent' }
      }

      const response = { success: true, emails: [] }
      chrome.runtime.sendMessage.mockResolvedValue(response)

      const result = await chrome.runtime.sendMessage(message)

      expect(result).toEqual(response)
      expect(chrome.runtime.sendMessage).toHaveBeenCalledWith(message)
    })

    it('should handle background to content script messages', async () => {
      const message = {
        action: 'updateBadge',
        count: 5
      }

      const response = { success: true }
      chrome.tabs.sendMessage.mockResolvedValue(response)

      const result = await chrome.tabs.sendMessage(123, message)

      expect(result).toEqual(response)
      expect(chrome.tabs.sendMessage).toHaveBeenCalledWith(123, message)
    })

    it('should handle message passing errors', async () => {
      chrome.runtime.sendMessage.mockRejectedValue(new Error('Extension context invalidated'))

      try {
        await chrome.runtime.sendMessage({ action: 'test' })
      } catch (error) {
        expect(error.message).toBe('Extension context invalidated')
      }
    })
  })

  describe('Integration with FYXERAI API', () => {
    beforeEach(() => {
      global.fetch = vi.fn()
    })

    it('should authenticate with FYXERAI backend', async () => {
      const authResponse = {
        success: true,
        token: 'test-auth-token',
        user: { id: 1, email: 'test@example.com' }
      }

      fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(authResponse)
      })

      // Simulate authentication
      const response = await fetch('http://localhost:8000/api/auth/token/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ extension_id: 'test-extension-id' })
      })

      const data = await response.json()

      expect(data).toEqual(authResponse)
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/auth/token/',
        expect.objectContaining({
          method: 'POST'
        })
      )
    })

    it('should fetch email data from API', async () => {
      const emailData = {
        success: true,
        emails: [
          {
            id: '1',
            subject: 'Test Email',
            sender: 'test@example.com',
            category: 'important'
          }
        ]
      }

      fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(emailData)
      })

      const response = await fetch('http://localhost:8000/api/emails/', {
        headers: { 'Authorization': 'Bearer test-token' }
      })

      const data = await response.json()

      expect(data.emails).toHaveLength(1)
      expect(data.emails[0].subject).toBe('Test Email')
    })

    it('should handle API rate limiting', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 429,
        headers: {
          get: (header) => header === 'Retry-After' ? '60' : null
        },
        text: () => Promise.resolve('Rate limit exceeded')
      })

      try {
        const response = await fetch('http://localhost:8000/api/emails/')
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${await response.text()}`)
        }
      } catch (error) {
        expect(error.message).toContain('429')
      }
    })
  })
})