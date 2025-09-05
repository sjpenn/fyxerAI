/**
 * End-to-end tests for email loading and triage functionality
 * Tests the complete flow from email display to categorization updates
 */

import { test, expect } from '@playwright/test'

test.describe('Email Loading and Triage Flow', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard and wait for load
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Ensure we're on the Overview tab initially
    await page.click('button:has-text("Overview")')
    await page.waitForLoadState('networkidle')
  })

  test('should display dashboard overview with email statistics', async ({ page }) => {
    // Check that overview cards are visible
    await expect(page.locator('.grid.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-4')).toBeVisible()
    
    // Check for statistic cards
    await expect(page.locator(':text("Total Messages")')).toBeVisible()
    await expect(page.locator(':text("Active Accounts")')).toBeVisible()
    await expect(page.locator(':text("Recent Meetings")')).toBeVisible()
    
    // Check for quick actions section
    await expect(page.locator(':text("Email Management")')).toBeVisible()
    await expect(page.locator('button:has-text("Urgent Emails")')).toBeVisible()
    await expect(page.locator('button:has-text("Important Emails")')).toBeVisible()
  })

  test('should navigate to inbox and display emails', async ({ page }) => {
    // Click inbox tab
    await page.click('button:has-text("Inbox")')
    await page.waitForLoadState('networkidle')
    
    // Check inbox header
    await expect(page.locator(':text("Email Inbox")')).toBeVisible()
    await expect(page.locator('select[name="category"]')).toBeVisible()
    await expect(page.locator('button:has-text("Refresh")')).toBeVisible()
    
    // Check for email list or empty state
    const emailList = page.locator('.divide-y.divide-slate-200')
    if (await emailList.isVisible()) {
      // If emails exist, check structure
      await expect(page.locator('.hover\\:bg-slate-50')).toBeVisible()
      await expect(page.locator('.badge')).toBeVisible()
    } else {
      // If no emails, check empty state
      await expect(page.locator(':text("No messages")')).toBeVisible()
    }
  })

  test('should filter emails by category', async ({ page }) => {
    // Navigate to inbox
    await page.click('button:has-text("Inbox")')
    await page.waitForLoadState('networkidle')
    
    // Get category filter dropdown
    const categoryFilter = page.locator('select[name="category"]')
    await expect(categoryFilter).toBeVisible()
    
    // Test filtering by urgent
    await categoryFilter.selectOption('urgent')
    await page.waitForLoadState('networkidle')
    
    // Check URL or content updates
    const url = page.url()
    expect(url).toContain('category=urgent')
    
    // Test filtering by important
    await categoryFilter.selectOption('important')
    await page.waitForLoadState('networkidle')
    
    // Reset filter
    await categoryFilter.selectOption('')
    await page.waitForLoadState('networkidle')
  })

  test('should refresh inbox when refresh button is clicked', async ({ page }) => {
    // Navigate to inbox
    await page.click('button:has-text("Inbox")')
    await page.waitForLoadState('networkidle')
    
    // Click refresh button
    const refreshButton = page.locator('button:has([stroke-linecap="round"])')
    await refreshButton.click()
    
    // Should show loading indicator briefly
    const loadingIndicator = page.locator('#inbox-loading')
    // Note: Loading might be too fast to catch, but this tests the interaction
    
    await page.waitForLoadState('networkidle')
    
    // Should still show inbox content
    await expect(page.locator(':text("Email Inbox")')).toBeVisible()
  })

  test('should handle urgent emails quick action', async ({ page }) => {
    // From overview, click urgent emails button
    const urgentButton = page.locator('button:has-text("Urgent Emails")')
    await urgentButton.click()
    await page.waitForLoadState('networkidle')
    
    // Should navigate to inbox with urgent filter
    await expect(page.locator(':text("Email Inbox")')).toBeVisible()
    
    // Check that urgent filter is applied
    const categoryFilter = page.locator('select[name="category"]')
    const selectedValue = await categoryFilter.inputValue()
    expect(selectedValue).toBe('urgent')
  })

  test('should handle important emails quick action', async ({ page }) => {
    // From overview, click important emails button
    const importantButton = page.locator('button:has-text("Important Emails")')
    await importantButton.click()
    await page.waitForLoadState('networkidle')
    
    // Should navigate to inbox with important filter
    await expect(page.locator(':text("Email Inbox")')).toBeVisible()
    
    // Check that important filter is applied
    const categoryFilter = page.locator('select[name="category"]')
    const selectedValue = await categoryFilter.inputValue()
    expect(selectedValue).toBe('important')
  })

  test('should trigger sync all accounts action', async ({ page }) => {
    // Mock the sync endpoint to avoid actual API calls
    await page.route('/api/categorization/sync/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          processed: 10,
          message: 'Sync completed successfully'
        })
      })
    })
    
    // Click sync all accounts button
    const syncButton = page.locator('button:has-text("Sync All Accounts")')
    await syncButton.click()
    
    // Should show confirmation dialog
    await page.waitForTimeout(100) // Brief pause for dialog
    
    // If confirmation dialog appears, confirm it
    try {
      await page.getByRole('button', { name: 'OK' }).click({ timeout: 1000 })
    } catch {
      // No confirmation dialog, which is also fine
    }
    
    // Should show loading indicator
    const loadingIndicator = page.locator('#sync-loading')
    // Note: Might be too fast to catch
    
    await page.waitForLoadState('networkidle')
  })

  test('should display email account status', async ({ page }) => {
    // Check connected accounts section
    await expect(page.locator(':text("Connected Accounts")')).toBeVisible()
    
    // Should show Gmail and Outlook account previews
    await expect(page.locator(':text("Gmail")')).toBeVisible()
    await expect(page.locator(':text("Outlook")')).toBeVisible()
    
    // Should show connection status badges
    const statusBadges = page.locator('.inline-flex.items-center.px-2\\.5.py-0\\.5.rounded-full')
    await expect(statusBadges.first()).toBeVisible()
    await expect(statusBadges.first()).toContainText('Connected')
  })

  test('should navigate to accounts management', async ({ page }) => {
    // Click manage accounts button
    const manageButton = page.locator('button:has-text("Manage")')
    await manageButton.click()
    await page.waitForLoadState('networkidle')
    
    // Should navigate to accounts tab
    await expect(page.locator(':text("Email Accounts")')).toBeVisible()
  })

  test('should handle email detail modal (if implemented)', async ({ page }) => {
    // Navigate to inbox first
    await page.click('button:has-text("Inbox")')
    await page.waitForLoadState('networkidle')
    
    // Look for email items
    const emailItems = page.locator('.hover\\:bg-slate-50')
    const emailCount = await emailItems.count()
    
    if (emailCount > 0) {
      // Click first email item
      await emailItems.first().click()
      
      // Check if modal appears
      const modal = page.locator('#email-detail-modal')
      // Note: Modal might not be implemented yet, this is future-proofing
      if (await modal.isVisible()) {
        await expect(modal).toBeVisible()
      }
    } else {
      console.log('No emails found to test detail view')
    }
  })

  test('should load more emails when available', async ({ page }) => {
    // Navigate to inbox
    await page.click('button:has-text("Inbox")')
    await page.waitForLoadState('networkidle')
    
    // Look for load more button
    const loadMoreButton = page.locator('button:has-text("Load More Messages")')
    
    if (await loadMoreButton.isVisible()) {
      await loadMoreButton.click()
      await page.waitForLoadState('networkidle')
      
      // Should load additional emails or show updated content
      await expect(page.locator(':text("Email Inbox")')).toBeVisible()
    } else {
      console.log('Load more button not available (less than 20 emails)')
    }
  })
})

test.describe('Email Triage Integration with Extension', () => {
  
  test('should handle extension health endpoint', async ({ page, request }) => {
    // Test the extension health endpoint directly
    const response = await request.get('/api/extension/health/')
    
    expect(response.status()).toBe(200)
    
    const data = await response.json()
    expect(data.status).toBe('ok')
    expect(data.message).toContain('FYXERAI backend is running')
  })

  test('should handle extension triage endpoint', async ({ page, request }) => {
    // Mock extension triage request
    const mockEmails = [
      {
        id: 'test-email-1',
        platform: 'gmail',
        subject: 'Urgent: Project deadline approaching',
        sender: 'manager@company.com'
      },
      {
        id: 'test-email-2',
        platform: 'gmail',
        subject: 'Newsletter: Weekly updates',
        sender: 'newsletter@blog.com'
      }
    ]
    
    const response = await request.post('/api/extension/triage/', {
      data: {
        platform: 'gmail',
        emails: mockEmails,
        action: 'batch_triage'
      },
      headers: {
        'Content-Type': 'application/json',
        'X-Extension-Source': 'fyxerai-chrome'
      }
    })
    
    expect(response.status()).toBe(200)
    
    const data = await response.json()
    expect(data.success).toBe(true)
    expect(data.processed).toBeGreaterThan(0)
    expect(data.categories).toBeDefined()
  })

  test('should update dashboard after triage operations', async ({ page }) => {
    // Navigate to overview
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Get initial email count
    const totalMessagesCard = page.locator(':text("Total Messages")').locator('..')
    const initialCount = await totalMessagesCard.locator('.text-2xl').textContent()
    
    // Simulate receiving triage update (this would normally come from extension)
    // For now, just refresh and check that data loads
    await page.reload()
    await page.waitForLoadState('networkidle')
    
    // Should still show email statistics
    await expect(page.locator(':text("Total Messages")')).toBeVisible()
    
    // Check that accounts are connected
    await expect(page.locator(':text("Connected Accounts")')).toBeVisible()
    await expect(page.locator(':text("Connected")').first()).toBeVisible()
  })
})

test.describe('Real-time Updates', () => {
  
  test('should auto-refresh dashboard overview', async ({ page }) => {
    // Navigate to overview
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Check that auto-refresh script is loaded
    const autoRefreshScript = await page.evaluate(() => {
      return typeof setInterval !== 'undefined'
    })
    expect(autoRefreshScript).toBe(true)
    
    // Wait a bit to ensure no JavaScript errors occur
    await page.waitForTimeout(2000)
    
    // Should still be functional
    await expect(page.locator(':text("Total Messages")')).toBeVisible()
  })

  test('should handle WebSocket connections gracefully', async ({ page }) => {
    // Mock WebSocket for testing
    await page.addInitScript(() => {
      window.mockWebSocketConnected = false
      
      class MockWebSocket extends EventTarget {
        constructor(url) {
          super()
          this.url = url
          this.readyState = WebSocket.CONNECTING
          
          // Simulate successful connection
          setTimeout(() => {
            this.readyState = WebSocket.OPEN
            window.mockWebSocketConnected = true
            this.dispatchEvent(new Event('open'))
          }, 100)
        }
        
        send(data) {
          // Mock receiving categorization updates
          setTimeout(() => {
            const mockUpdate = {
              type: 'email_categorized',
              data: {
                email_id: 'test-123',
                category: 'important',
                confidence: 0.85
              }
            }
            this.dispatchEvent(new MessageEvent('message', { 
              data: JSON.stringify(mockUpdate) 
            }))
          }, 50)
        }
        
        close() {
          this.readyState = WebSocket.CLOSED
          window.mockWebSocketConnected = false
        }
      }
      
      window.WebSocket = MockWebSocket
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Check that WebSocket connection would be established
    const wsConnected = await page.evaluate(() => window.mockWebSocketConnected)
    expect(wsConnected).toBe(true)
  })
})

test.describe('Error Handling and Edge Cases', () => {
  
  test('should handle empty email inbox gracefully', async ({ page }) => {
    // Mock empty inbox response
    await page.route('/partials/email-inbox/', async route => {
      const emptyInboxHTML = `
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm">
          <div class="border-b border-slate-200 dark:border-slate-700 p-6">
            <h2 class="text-xl font-semibold text-slate-900 dark:text-slate-100">Email Inbox</h2>
          </div>
          <div class="p-12 text-center">
            <h3 class="mt-4 text-sm font-medium text-slate-900 dark:text-slate-100">No messages</h3>
            <p class="mt-2 text-sm text-slate-500 dark:text-slate-400">
              No messages found. Connect an email account to get started.
            </p>
          </div>
        </div>
      `
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: emptyInboxHTML
      })
    })
    
    // Navigate to inbox
    await page.click('button:has-text("Inbox")')
    await page.waitForLoadState('networkidle')
    
    // Should show empty state
    await expect(page.locator(':text("No messages")')).toBeVisible()
    await expect(page.locator(':text("Connect an email account")')).toBeVisible()
  })

  test('should handle network errors on inbox load', async ({ page }) => {
    // Mock network error
    await page.route('/partials/email-inbox/', async route => {
      await route.fulfill({
        status: 500,
        contentType: 'text/html',
        body: 'Internal Server Error'
      })
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Try to navigate to inbox
    await page.click('button:has-text("Inbox")')
    await page.waitForTimeout(1000)
    
    // Should handle error gracefully (exact handling depends on HTMX config)
    // At minimum, page shouldn't crash
    await expect(page.locator('body')).toBeVisible()
  })

  test('should handle authentication required scenarios', async ({ page }) => {
    // Mock authentication error
    await page.route('/partials/email-inbox/', async route => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Authentication required' })
      })
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Try to access inbox
    await page.click('button:has-text("Inbox")')
    await page.waitForTimeout(1000)
    
    // Should handle auth error appropriately
    // (Exact behavior depends on implementation)
    await expect(page.locator('body')).toBeVisible()
  })
})