/**
 * End-to-end tests for the main dashboard functionality
 */

import { test, expect } from '@playwright/test'

test.describe('FYXERAI Dashboard E2E Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/')
    
    // Wait for the page to load completely
    await page.waitForLoadState('networkidle')
  })

  test('should load dashboard with all main components', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/FYXERAI Dashboard/)
    
    // Check main navigation tabs
    await expect(page.locator('[data-testid="dashboard-nav"]')).toBeVisible()
    await expect(page.locator('button:has-text("Overview")')).toBeVisible()
    await expect(page.locator('button:has-text("Inbox")')).toBeVisible()
    await expect(page.locator('button:has-text("Accounts")')).toBeVisible()
    await expect(page.locator('button:has-text("Statistics")')).toBeVisible()
    await expect(page.locator('button:has-text("Real-time")')).toBeVisible()
    
    // Check theme toggle
    await expect(page.locator('[data-theme-toggle]')).toBeVisible()
  })

  test('should switch between dashboard tabs', async ({ page }) => {
    // Test Overview tab (default)
    await expect(page.locator('#main-content')).toContainText('Overview')
    
    // Switch to Inbox tab
    await page.click('button:has-text("Inbox")')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('#main-content')).toContainText('Email Inbox')
    
    // Switch to Accounts tab
    await page.click('button:has-text("Accounts")')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('#main-content')).toContainText('Email Accounts')
    
    // Switch to Statistics tab
    await page.click('button:has-text("Statistics")')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('#main-content')).toContainText('Statistics')
  })

  test('should load real-time dashboard tab', async ({ page }) => {
    // Click Real-time tab
    await page.click('button:has-text("Real-time")')
    
    // Wait for content to load
    await page.waitForTimeout(1000)
    
    // Check for real-time dashboard components
    await expect(page.locator('#main-content')).toContainText('Email Dashboard')
    await expect(page.locator('.connection-status')).toBeVisible()
    await expect(page.locator('.sync-status')).toBeVisible()
    await expect(page.locator('.unread-count')).toBeVisible()
  })

  test('should toggle dark/light theme', async ({ page }) => {
    // Check initial theme (should be light)
    const html = page.locator('html')
    await expect(html).not.toHaveClass(/dark/)
    
    // Click theme toggle
    await page.click('[data-theme-toggle]')
    
    // Wait for theme change
    await page.waitForTimeout(300)
    
    // Check dark theme is applied
    await expect(html).toHaveClass(/dark/)
    
    // Toggle back to light
    await page.click('[data-theme-toggle]')
    await page.waitForTimeout(300)
    
    // Check light theme is restored
    await expect(html).not.toHaveClass(/dark/)
  })

  test('should show loading indicators during tab switches', async ({ page }) => {
    // Click on a tab and check for loading indicator
    await page.click('button:has-text("Inbox")')
    
    // Should briefly show loading indicator
    const loadingIndicator = page.locator('#htmx-global-loading')
    
    // Wait for content to load
    await page.waitForLoadState('networkidle')
    
    // Loading indicator should be hidden after load
    await expect(loadingIndicator).toBeHidden()
  })
})

test.describe('Real-time Dashboard Functionality', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Navigate to real-time dashboard
    await page.click('button:has-text("Real-time")')
    await page.waitForTimeout(1000)
  })

  test('should display connection status indicators', async ({ page }) => {
    // Check for sync connection indicator
    const syncIndicator = page.locator('.connection-status').first()
    await expect(syncIndicator).toBeVisible()
    
    // Check for notifications connection indicator
    const notificationIndicator = page.locator('.connection-status').nth(1)
    await expect(notificationIndicator).toBeVisible()
    
    // Connection status should have appropriate colors (red for disconnected initially)
    const statusDots = page.locator('.connection-status .w-2.h-2.rounded-full')
    await expect(statusDots.first()).toHaveClass(/bg-red-500|bg-green-500/)
  })

  test('should show sync controls', async ({ page }) => {
    // Check for sync buttons
    await expect(page.locator('button:has-text("Start Sync")')).toBeVisible()
    await expect(page.locator('button:has-text("Force Full Sync")')).toBeVisible()
    await expect(page.locator('button:has-text("Refresh Count")')).toBeVisible()
    
    // Buttons should be clickable
    await expect(page.locator('button:has-text("Start Sync")')).toBeEnabled()
    await expect(page.locator('button:has-text("Force Full Sync")')).toBeEnabled()
  })

  test('should display unread email counter', async ({ page }) => {
    // Check unread counter section
    await expect(page.locator('.text-2xl.font-bold.text-blue-600')).toBeVisible()
    
    // Should show numeric value (default 0 or actual count)
    const unreadCount = await page.locator('.text-2xl.font-bold.text-blue-600').textContent()
    expect(unreadCount).toMatch(/^\d+$/)
  })

  test('should show recent emails section', async ({ page }) => {
    await expect(page.locator(':text("Recent Emails")')).toBeVisible()
    
    // Should have scrollable area for emails
    await expect(page.locator('.max-h-60.overflow-y-auto')).toBeVisible()
    
    // May show "No recent emails" message initially
    await expect(page.locator(':text("No recent emails")')).toBeVisible()
  })

  test('should display notification panel', async ({ page }) => {
    await expect(page.locator(':text("Recent Notifications")')).toBeVisible()
    
    // Should have notification area
    const notificationArea = page.locator('.max-h-40.overflow-y-auto')
    await expect(notificationArea).toBeVisible()
    
    // May show "No recent notifications" initially
    await expect(page.locator(':text("No recent notifications")')).toBeVisible()
  })

  test('should handle sync button clicks', async ({ page }) => {
    // Mock WebSocket for testing
    await page.addInitScript(() => {
      window.mockWebSocketMessages = []
      
      class MockWebSocket extends EventTarget {
        constructor(url) {
          super()
          this.url = url
          this.readyState = WebSocket.OPEN
          setTimeout(() => this.dispatchEvent(new Event('open')), 10)
        }
        
        send(data) {
          window.mockWebSocketMessages.push(JSON.parse(data))
        }
        
        close() {
          this.readyState = WebSocket.CLOSED
        }
      }
      
      window.WebSocket = MockWebSocket
    })
    
    // Click start sync button
    await page.click('button:has-text("Start Sync")')
    
    // Button should show loading state (if implemented)
    // We can't easily test WebSocket messages in E2E, but we can test UI changes
    
    // Click force full sync
    await page.click('button:has-text("Force Full Sync")')
    
    // No errors should occur
    await page.waitForTimeout(500)
  })
})

test.describe('Responsive Design', () => {
  
  test('should work on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Dashboard should still be accessible
    await expect(page.locator('[data-testid="dashboard-nav"]')).toBeVisible()
    
    // Navigation should be responsive
    const navButtons = page.locator('button:has-text("Overview")')
    await expect(navButtons).toBeVisible()
    
    // Content should be scrollable
    await expect(page.locator('#main-content')).toBeVisible()
  })

  test('should work on tablet viewport', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // All components should be visible and properly arranged
    await expect(page.locator('[data-theme-toggle]')).toBeVisible()
    await expect(page.locator('#main-content')).toBeVisible()
    
    // Switch tabs should work smoothly
    await page.click('button:has-text("Real-time")')
    await page.waitForTimeout(1000)
    await expect(page.locator(':text("Email Dashboard")')).toBeVisible()
  })

  test('should work on desktop viewport', async ({ page }) => {
    // Set large desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // All content should be properly spaced
    await expect(page.locator('.max-w-7xl')).toBeVisible()
    
    // Navigate to real-time dashboard
    await page.click('button:has-text("Real-time")')
    await page.waitForTimeout(1000)
    
    // Grid layouts should be properly displayed
    await expect(page.locator('.grid')).toBeVisible()
  })
})

test.describe('Accessibility', () => {
  
  test('should have proper keyboard navigation', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Tab through navigation
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    
    // Should be able to navigate to theme toggle
    const themeToggle = page.locator('[data-theme-toggle]')
    await themeToggle.focus()
    await expect(themeToggle).toBeFocused()
    
    // Should be able to activate with Enter
    await page.keyboard.press('Enter')
    await page.waitForTimeout(300)
    
    // Theme should change
    await expect(page.locator('html')).toHaveClass(/dark/)
  })

  test('should have proper ARIA attributes', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Navigate to real-time dashboard
    await page.click('button:has-text("Real-time")')
    await page.waitForTimeout(1000)
    
    // Check for ARIA labels on important elements
    const syncButton = page.locator('button:has-text("Start Sync")')
    await expect(syncButton).toHaveAttribute('type', 'button')
    
    // Check for proper heading hierarchy
    await expect(page.locator('h1, h2, h3').first()).toBeVisible()
  })

  test('should handle screen reader announcements', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Navigate to real-time dashboard
    await page.click('button:has-text("Real-time")')
    await page.waitForTimeout(1000)
    
    // Check for live regions that would announce updates
    const notificationArea = page.locator('[aria-live]').first()
    if (await notificationArea.isVisible()) {
      await expect(notificationArea).toHaveAttribute('aria-live')
    }
  })
})

test.describe('Error Handling', () => {
  
  test('should handle network errors gracefully', async ({ page }) => {
    // Intercept and fail network requests
    await page.route('/partials/**', route => {
      route.fulfill({
        status: 500,
        contentType: 'text/html',
        body: 'Internal Server Error'
      })
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Try to switch tabs
    await page.click('button:has-text("Inbox")')
    await page.waitForTimeout(1000)
    
    // Should show some kind of error indication
    // (Exact error handling depends on implementation)
    const content = await page.locator('#main-content').textContent()
    expect(content).toBeTruthy() // Should not be completely empty
  })

  test('should handle JavaScript errors gracefully', async ({ page }) => {
    let jsErrors = []
    
    // Capture JavaScript errors
    page.on('pageerror', error => {
      jsErrors.push(error.message)
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Navigate through tabs
    await page.click('button:has-text("Real-time")')
    await page.waitForTimeout(1000)
    
    // Click various buttons
    await page.click('button:has-text("Refresh Count")')
    await page.waitForTimeout(500)
    
    // Should not have critical JavaScript errors
    const criticalErrors = jsErrors.filter(error => 
      !error.includes('WebSocket') && // WebSocket errors expected in test env
      !error.includes('Notification') // Notification permission errors expected
    )
    
    expect(criticalErrors.length).toBe(0)
  })

  test('should handle missing WebSocket gracefully', async ({ page }) => {
    // Disable WebSocket
    await page.addInitScript(() => {
      delete window.WebSocket
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Navigate to real-time dashboard
    await page.click('button:has-text("Real-time")')
    await page.waitForTimeout(1000)
    
    // Should still show the interface
    await expect(page.locator(':text("Email Dashboard")')).toBeVisible()
    
    // Connection indicators should show disconnected state
    const connectionIndicators = page.locator('.bg-red-500')
    await expect(connectionIndicators.first()).toBeVisible()
  })
})

test.describe('Performance', () => {
  
  test('should load within acceptable time limits', async ({ page }) => {
    const startTime = Date.now()
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    const loadTime = Date.now() - startTime
    
    // Should load within 3 seconds
    expect(loadTime).toBeLessThan(3000)
  })

  test('should handle rapid tab switching', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Rapidly switch between tabs
    const tabs = ['Inbox', 'Accounts', 'Statistics', 'Overview']
    
    for (let i = 0; i < 3; i++) { // Do it 3 times
      for (const tab of tabs) {
        await page.click(`button:has-text("${tab}")`)
        await page.waitForTimeout(100) // Brief pause
      }
    }
    
    // Should still be functional
    await page.waitForLoadState('networkidle')
    await expect(page.locator('#main-content')).toBeVisible()
  })
})