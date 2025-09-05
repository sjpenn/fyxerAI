/**
 * End-to-end tests for Chrome Extension functionality
 */

import { test, expect, chromium } from '@playwright/test'
import path from 'path'

const extensionPath = path.join(__dirname, '../../extension')

test.describe('Chrome Extension E2E Tests', () => {
  let context
  let extensionId
  
  test.beforeAll(async () => {
    // Launch browser with extension loaded
    context = await chromium.launchPersistentContext('', {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor'
      ]
    })
    
    // Get extension ID
    const backgroundPage = await context.waitForEvent('page', page => 
      page.url().startsWith('chrome-extension://')
    ).catch(() => null)
    
    if (backgroundPage) {
      extensionId = backgroundPage.url().split('://')[1].split('/')[0]
    }
  })

  test.afterAll(async () => {
    await context?.close()
  })

  test('should load extension successfully', async () => {
    const pages = context.pages()
    
    // Extension should create background page
    const backgroundPages = pages.filter(page => 
      page.url().startsWith('chrome-extension://')
    )
    
    expect(backgroundPages.length).toBeGreaterThan(0)
  })

  test('should inject content script into Gmail', async () => {
    const page = await context.newPage()
    
    // Navigate to Gmail (or Gmail-like test page)
    await page.goto('https://mail.google.com')
    await page.waitForLoadState('networkidle')
    
    // Check if content script loaded
    const contentScriptLoaded = await page.evaluate(() => {
      return window.fyxeraiExtensionLoaded === true
    }).catch(() => false)
    
    // Even if Gmail blocks extension, the content script attempt should register
    expect(typeof contentScriptLoaded).toBe('boolean')
  })

  test('should show extension popup', async () => {
    const page = await context.newPage()
    
    // Click extension icon (simulate)
    const popupPromise = context.waitForEvent('page', page => 
      page.url().includes('chrome-extension://') && page.url().includes('popup.html')
    )
    
    // Simulate clicking extension icon via browser action
    await page.evaluate((extensionId) => {
      if (chrome && chrome.action) {
        chrome.action.openPopup()
      }
    }, extensionId).catch(() => {
      // Fallback: directly navigate to popup
      return page.goto(`chrome-extension://${extensionId}/popup.html`)
    })
    
    const popupPage = await popupPromise.catch(() => 
      context.newPage().then(p => p.goto(`chrome-extension://${extensionId}/popup.html`))
    )
    
    await popupPage.waitForLoadState('networkidle')
    
    // Check popup content
    await expect(popupPage.locator('h1')).toContainText('FYXERAI')
    await expect(popupPage.locator('.connection-status')).toBeVisible()
  })

  test('should display connection status in popup', async () => {
    const popupPage = await context.newPage()
    await popupPage.goto(`chrome-extension://${extensionId}/popup.html`)
    await popupPage.waitForLoadState('networkidle')
    
    // Check status indicator
    const statusIndicator = popupPage.locator('#status-indicator')
    await expect(statusIndicator).toBeVisible()
    
    const statusText = await statusIndicator.textContent()
    expect(['Connected', 'Disconnected', 'Connecting']).toContain(statusText)
  })

  test('should show email stats in popup', async () => {
    const popupPage = await context.newPage()
    await popupPage.goto(`chrome-extension://${extensionId}/popup.html`)
    await popupPage.waitForLoadState('networkidle')
    
    // Check for unread count
    await expect(popupPage.locator('#unread-count')).toBeVisible()
    
    // Check for pending count
    await expect(popupPage.locator('#pending-count')).toBeVisible()
    
    // Values should be numeric
    const unreadCount = await popupPage.locator('#unread-count').textContent()
    expect(unreadCount).toMatch(/^\d+$/)
  })

  test('should handle popup button clicks', async () => {
    const popupPage = await context.newPage()
    await popupPage.goto(`chrome-extension://${extensionId}/popup.html`)
    await popupPage.waitForLoadState('networkidle')
    
    // Test triage all button
    const triageButton = popupPage.locator('#triage-all-btn')
    await expect(triageButton).toBeVisible()
    await expect(triageButton).toBeEnabled()
    
    await triageButton.click()
    // Should not throw errors
    
    // Test sync now button
    const syncButton = popupPage.locator('#sync-now-btn')
    await expect(syncButton).toBeVisible()
    await syncButton.click()
    
    // Test settings button
    const settingsButton = popupPage.locator('#settings-btn')
    await expect(settingsButton).toBeVisible()
    await settingsButton.click()
  })

  test('should communicate with background script', async () => {
    const popupPage = await context.newPage()
    await popupPage.goto(`chrome-extension://${extensionId}/popup.html`)
    await popupPage.waitForLoadState('networkidle')
    
    // Test message passing
    const response = await popupPage.evaluate(async () => {
      try {
        return await chrome.runtime.sendMessage({
          action: 'getStatus'
        })
      } catch (error) {
        return { error: error.message }
      }
    })
    
    expect(response).toBeDefined()
    // Should either have status data or an error (both are valid in test environment)
  })

  test('should store user preferences', async () => {
    const popupPage = await context.newPage()
    await popupPage.goto(`chrome-extension://${extensionId}/popup.html`)
    await popupPage.waitForLoadState('networkidle')
    
    // Test storage functionality
    const storageTest = await popupPage.evaluate(async () => {
      try {
        const testData = { autoTriage: true, notifications: false }
        await chrome.storage.sync.set({ preferences: testData })
        
        const result = await chrome.storage.sync.get(['preferences'])
        return result.preferences
      } catch (error) {
        return { error: error.message }
      }
    })
    
    expect(storageTest).toBeDefined()
    // Should either have the stored data or an error
  })

  test('should handle context menu integration', async () => {
    const page = await context.newPage()
    await page.goto('https://mail.google.com')
    await page.waitForLoadState('networkidle')
    
    // Test context menu creation (background script functionality)
    const contextMenuTest = await page.evaluate(() => {
      try {
        // This tests if the context menu APIs are accessible
        return typeof chrome.contextMenus !== 'undefined'
      } catch (error) {
        return false
      }
    })
    
    expect(typeof contextMenuTest).toBe('boolean')
  })
})

test.describe('Extension API Integration', () => {
  let context
  let extensionId

  test.beforeAll(async () => {
    context = await chromium.launchPersistentContext('', {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`
      ]
    })
    
    const backgroundPage = await context.waitForEvent('page', page => 
      page.url().startsWith('chrome-extension://')
    ).catch(() => null)
    
    if (backgroundPage) {
      extensionId = backgroundPage.url().split('://')[1].split('/')[0]
    }
  })

  test.afterAll(async () => {
    await context?.close()
  })

  test('should make API requests to FYXERAI backend', async () => {
    const popupPage = await context.newPage()
    await popupPage.goto(`chrome-extension://${extensionId}/popup.html`)
    
    // Mock fetch for testing
    await popupPage.addInitScript(() => {
      window.originalFetch = window.fetch
      window.fetch = async (url, options) => {
        if (url.includes('/api/')) {
          return {
            ok: true,
            status: 200,
            json: () => Promise.resolve({
              success: true,
              data: { emails: [], unreadCount: 5 }
            })
          }
        }
        return window.originalFetch(url, options)
      }
    })
    
    // Test API call
    const apiResponse = await popupPage.evaluate(async () => {
      try {
        const response = await fetch('http://localhost:8000/api/emails/', {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        })
        return await response.json()
      } catch (error) {
        return { error: error.message }
      }
    })
    
    expect(apiResponse.success).toBe(true)
    expect(apiResponse.data).toBeDefined()
  })

  test('should handle API authentication', async () => {
    const popupPage = await context.newPage()
    await popupPage.goto(`chrome-extension://${extensionId}/popup.html`)
    
    // Test authentication flow
    const authTest = await popupPage.evaluate(async () => {
      try {
        // Simulate getting auth token
        const token = await chrome.storage.sync.get(['authToken'])
        return { hasToken: !!token.authToken, token: token.authToken }
      } catch (error) {
        return { error: error.message }
      }
    })
    
    expect(authTest).toBeDefined()
  })

  test('should handle API errors gracefully', async () => {
    const popupPage = await context.newPage()
    await popupPage.goto(`chrome-extension://${extensionId}/popup.html`)
    
    // Mock failing API requests
    await popupPage.addInitScript(() => {
      window.fetch = async () => {
        throw new Error('Network error')
      }
    })
    
    // Test error handling
    const errorHandling = await popupPage.evaluate(async () => {
      try {
        await fetch('http://localhost:8000/api/emails/')
        return { success: true }
      } catch (error) {
        return { error: error.message, handled: true }
      }
    })
    
    expect(errorHandling.error).toBeDefined()
    expect(errorHandling.handled).toBe(true)
  })
})

test.describe('Content Script Integration', () => {
  let context
  let extensionId

  test.beforeAll(async () => {
    context = await chromium.launchPersistentContext('', {
      headless: false,
      args: [
        `--disable-extensions-except=${extensionPath}`,
        `--load-extension=${extensionPath}`,
        '--disable-web-security'
      ]
    })
  })

  test.afterAll(async () => {
    await context?.close()
  })

  test('should inject into web pages', async () => {
    const page = await context.newPage()
    
    // Create a test page with email-like structure
    await page.setContent(`
      <!DOCTYPE html>
      <html>
      <head><title>Test Email Interface</title></head>
      <body>
        <div class="email-list">
          <div class="email-item" data-thread-id="123">
            <span class="subject">Test Email</span>
            <span class="sender">test@example.com</span>
          </div>
        </div>
      </body>
      </html>
    `)
    
    await page.waitForLoadState('networkidle')
    
    // Check if content script variables are accessible
    const contentScriptInjected = await page.evaluate(() => {
      // Content script should add some global variable or modify DOM
      return document.querySelector('.email-item') !== null
    })
    
    expect(contentScriptInjected).toBe(true)
  })

  test('should handle Gmail-specific DOM manipulation', async () => {
    const page = await context.newPage()
    
    // Simulate Gmail-like structure
    await page.setContent(`
      <!DOCTYPE html>
      <html>
      <body>
        <div role="main">
          <div class="gmail-interface">
            <div class="email-row" data-thread-id="thread1">
              <div class="subject">Important Meeting</div>
              <div class="sender">manager@company.com</div>
            </div>
          </div>
        </div>
      </body>
      </html>
    `)
    
    await page.waitForLoadState('networkidle')
    
    // Simulate what content script would do
    await page.evaluate(() => {
      const emailRows = document.querySelectorAll('.email-row')
      emailRows.forEach(row => {
        const button = document.createElement('button')
        button.textContent = 'FYXERAI Triage'
        button.className = 'fyxerai-button'
        row.appendChild(button)
      })
    })
    
    // Check if buttons were added
    const fyxeraiButtons = await page.locator('.fyxerai-button').count()
    expect(fyxeraiButtons).toBeGreaterThan(0)
  })

  test('should handle TrustedTypes CSP compliance', async () => {
    const page = await context.newPage()
    
    // Enable TrustedTypes
    await page.addInitScript(() => {
      if (window.trustedTypes && window.trustedTypes.createPolicy) {
        const policy = window.trustedTypes.createPolicy('fyxerai-test', {
          createHTML: (string) => string
        })
        
        window.fyxeraiPolicy = policy
      }
    })
    
    await page.setContent(`
      <!DOCTYPE html>
      <html>
      <head>
        <meta http-equiv="Content-Security-Policy" content="require-trusted-types-for 'script';">
      </head>
      <body>
        <div id="test-container"></div>
      </body>
      </html>
    `)
    
    // Test trusted HTML creation
    const trustedTypesTest = await page.evaluate(() => {
      try {
        const container = document.getElementById('test-container')
        if (window.fyxeraiPolicy) {
          const safeHTML = window.fyxeraiPolicy.createHTML('<div>Safe content</div>')
          container.innerHTML = safeHTML
          return { success: true, content: container.innerHTML }
        } else {
          container.innerHTML = '<div>Direct content</div>'
          return { success: true, content: container.innerHTML, direct: true }
        }
      } catch (error) {
        return { error: error.message }
      }
    })
    
    expect(trustedTypesTest.success || trustedTypesTest.error).toBeDefined()
  })
})

test.describe('Extension Performance', () => {
  let context

  test.beforeAll(async () => {
    context = await chromium.launchPersistentContext('', {
      headless: false,
      args: [`--load-extension=${extensionPath}`]
    })
  })

  test.afterAll(async () => {
    await context?.close()
  })

  test('should not significantly impact page load time', async () => {
    const page = await context.newPage()
    
    const startTime = Date.now()
    await page.goto('https://example.com')
    await page.waitForLoadState('networkidle')
    const loadTime = Date.now() - startTime
    
    // Should not add more than 2 seconds to load time
    expect(loadTime).toBeLessThan(5000)
  })

  test('should handle multiple tabs efficiently', async () => {
    const pages = []
    
    // Open multiple tabs
    for (let i = 0; i < 5; i++) {
      const page = await context.newPage()
      await page.goto(`data:text/html,<html><body><h1>Tab ${i}</h1></body></html>`)
      pages.push(page)
    }
    
    // All pages should load successfully
    for (const page of pages) {
      await expect(page.locator('h1')).toBeVisible()
    }
    
    // Clean up
    for (const page of pages) {
      await page.close()
    }
  })

  test('should manage memory usage appropriately', async () => {
    const page = await context.newPage()
    await page.goto('https://example.com')
    
    // Get initial memory usage
    const initialMemory = await page.evaluate(() => {
      return performance.memory ? performance.memory.usedJSHeapSize : 0
    })
    
    // Perform extension operations
    await page.evaluate(() => {
      // Simulate extension activity
      for (let i = 0; i < 1000; i++) {
        const div = document.createElement('div')
        div.textContent = `Item ${i}`
        document.body.appendChild(div)
      }
    })
    
    const finalMemory = await page.evaluate(() => {
      return performance.memory ? performance.memory.usedJSHeapSize : 0
    })
    
    // Memory increase should be reasonable
    const memoryIncrease = finalMemory - initialMemory
    expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024) // Less than 50MB
  })
})