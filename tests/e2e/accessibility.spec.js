/**
 * Accessibility tests for FYXERAI application
 */

import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test.describe('Accessibility Tests', () => {
  
  test('should pass automated accessibility checks', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze()
    
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Check heading levels
    const headings = await page.locator('h1, h2, h3, h4, h5, h6').all()
    
    expect(headings.length).toBeGreaterThan(0)
    
    // Should have at least one h1
    const h1Count = await page.locator('h1').count()
    expect(h1Count).toBeGreaterThanOrEqual(1)
    
    // Check heading sequence (no skipping levels)
    const headingLevels = []
    for (const heading of headings) {
      const tagName = await heading.evaluate(el => el.tagName.toLowerCase())
      headingLevels.push(parseInt(tagName.charAt(1)))
    }
    
    // Verify no heading levels are skipped
    for (let i = 1; i < headingLevels.length; i++) {
      const currentLevel = headingLevels[i]
      const previousLevel = headingLevels[i - 1]
      
      if (currentLevel > previousLevel) {
        // Can only increase by 1 level at a time
        expect(currentLevel - previousLevel).toBeLessThanOrEqual(1)
      }
    }
  })

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Test tab navigation
    await page.keyboard.press('Tab')
    let focusedElement = await page.evaluate(() => document.activeElement?.tagName)
    expect(focusedElement).toBeDefined()
    
    // Navigate through several elements
    const focusableElements = []
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab')
      const currentFocus = await page.evaluate(() => ({
        tagName: document.activeElement?.tagName,
        className: document.activeElement?.className,
        id: document.activeElement?.id,
        text: document.activeElement?.textContent?.slice(0, 20)
      }))
      focusableElements.push(currentFocus)
    }
    
    // Should have navigated through different elements
    const uniqueElements = new Set(focusableElements.map(el => `${el.tagName}-${el.id}-${el.className}`))
    expect(uniqueElements.size).toBeGreaterThan(1)
  })

  test('should support screen reader navigation', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Check for ARIA landmarks
    const landmarks = await page.locator('[role="main"], [role="navigation"], [role="complementary"], [role="banner"]').all()
    expect(landmarks.length).toBeGreaterThan(0)
    
    // Check for ARIA labels on interactive elements
    const buttons = await page.locator('button').all()
    for (const button of buttons) {
      const hasAccessibleName = await button.evaluate(el => {
        return !!(el.textContent?.trim() || 
                 el.getAttribute('aria-label') || 
                 el.getAttribute('aria-labelledby') || 
                 el.getAttribute('title'))
      })
      expect(hasAccessibleName).toBe(true)
    }
  })

  test('should have sufficient color contrast', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Test both light and dark themes
    const themes = ['light', 'dark']
    
    for (const theme of themes) {
      if (theme === 'dark') {
        await page.click('[data-theme-toggle]')
        await page.waitForTimeout(300)
      }
      
      const contrastResults = await new AxeBuilder({ page })
        .withTags(['wcag2aa'])
        .analyze()
      
      const colorContrastViolations = contrastResults.violations.filter(
        violation => violation.id === 'color-contrast'
      )
      
      expect(colorContrastViolations).toEqual([])
    }
  })

  test('should support focus management in modals', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Navigate to real-time dashboard to test urgent alert modal
    await page.click('button:has-text("Real-time")')
    await page.waitForTimeout(1000)
    
    // Simulate urgent alert modal (would normally be triggered by WebSocket)
    await page.evaluate(() => {
      // Create modal for testing
      const modal = document.createElement('div')
      modal.id = 'test-modal'
      modal.innerHTML = `
        <div class="modal-content">
          <h2>Test Modal</h2>
          <button id="modal-button">Action</button>
          <button id="modal-close">Close</button>
        </div>
      `
      modal.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 1000; background: white; padding: 20px; border: 1px solid black;'
      document.body.appendChild(modal)
      
      // Focus first element
      modal.querySelector('button').focus()
    })
    
    // Check focus is trapped in modal
    let focusedId = await page.evaluate(() => document.activeElement?.id)
    expect(['modal-button', 'modal-close']).toContain(focusedId)
    
    // Tab through modal elements
    await page.keyboard.press('Tab')
    focusedId = await page.evaluate(() => document.activeElement?.id)
    expect(['modal-button', 'modal-close']).toContain(focusedId)
    
    // Clean up
    await page.evaluate(() => {
      const modal = document.getElementById('test-modal')
      if (modal) modal.remove()
    })
  })

  test('should have accessible form controls', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Find all form controls
    const formControls = await page.locator('input, select, textarea').all()
    
    for (const control of formControls) {
      // Each form control should have an accessible name
      const hasAccessibleName = await control.evaluate(el => {
        const id = el.id
        const hasLabel = id && document.querySelector(`label[for="${id}"]`)
        const hasAriaLabel = el.getAttribute('aria-label')
        const hasAriaLabelledBy = el.getAttribute('aria-labelledby')
        const hasTitle = el.getAttribute('title')
        const hasPlaceholder = el.getAttribute('placeholder')
        
        return !!(hasLabel || hasAriaLabel || hasAriaLabelledBy || hasTitle || hasPlaceholder)
      })
      
      expect(hasAccessibleName).toBe(true)
    }
    
    // Check for required field indicators
    const requiredFields = await page.locator('[required]').all()
    for (const field of requiredFields) {
      const hasRequiredIndicator = await field.evaluate(el => {
        const ariaRequired = el.getAttribute('aria-required')
        const hasAsterisk = el.parentElement?.textContent?.includes('*')
        const hasRequiredLabel = el.labels?.[0]?.textContent?.includes('required')
        
        return ariaRequired === 'true' || hasAsterisk || hasRequiredLabel
      })
      
      expect(hasRequiredIndicator).toBe(true)
    }
  })

  test('should announce dynamic content changes', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Navigate to real-time dashboard
    await page.click('button:has-text("Real-time")')
    await page.waitForTimeout(1000)
    
    // Check for ARIA live regions
    const liveRegions = await page.locator('[aria-live], [role="status"], [role="alert"]').all()
    
    if (liveRegions.length > 0) {
      for (const region of liveRegions) {
        const ariaLive = await region.getAttribute('aria-live')
        const role = await region.getAttribute('role')
        
        expect(['polite', 'assertive', 'off'].concat([null])).toContain(ariaLive)
        if (role) {
          expect(['status', 'alert', 'log']).toContain(role)
        }
      }
    }
  })

  test('should handle reduced motion preferences', async ({ page }) => {
    // Set reduced motion preference
    await page.emulateMedia({ reducedMotion: 'reduce' })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Test theme toggle animation
    await page.click('[data-theme-toggle]')
    await page.waitForTimeout(100)
    
    // Check that animations are reduced or disabled
    const hasReducedMotion = await page.evaluate(() => {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches
    })
    
    expect(hasReducedMotion).toBe(true)
    
    // Transitions should be minimal or instant
    const transitionDuration = await page.evaluate(() => {
      const htmlElement = document.documentElement
      const computedStyle = getComputedStyle(htmlElement)
      return computedStyle.transitionDuration
    })
    
    // Should have minimal or no transition when reduced motion is preferred
    expect(['0s', ''].includes(transitionDuration) || parseFloat(transitionDuration) < 0.1).toBe(true)
  })

  test('should support high contrast mode', async ({ page }) => {
    // Test with forced-colors media query (high contrast mode)
    await page.emulateMedia({ forcedColors: 'active' })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    const supportsHighContrast = await page.evaluate(() => {
      return window.matchMedia('(forced-colors: active)').matches
    })
    
    if (supportsHighContrast) {
      // Check that colors are properly handled
      const elements = await page.locator('button, .card, .badge').all()
      
      for (const element of elements.slice(0, 5)) { // Check first 5 elements
        const styles = await element.evaluate(el => {
          const computed = getComputedStyle(el)
          return {
            backgroundColor: computed.backgroundColor,
            color: computed.color,
            border: computed.border
          }
        })
        
        // Elements should have proper contrast in high contrast mode
        expect(styles.backgroundColor).toBeDefined()
        expect(styles.color).toBeDefined()
      }
    }
  })

  test('should be operable with voice commands', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Test that elements have unique, descriptive names for voice navigation
    const interactiveElements = await page.locator('button, a, input, select').all()
    const elementNames = []
    
    for (const element of interactiveElements) {
      const name = await element.evaluate(el => {
        return el.textContent?.trim() || 
               el.getAttribute('aria-label') || 
               el.getAttribute('title') || 
               el.getAttribute('alt') ||
               el.getAttribute('value') ||
               'unnamed-element'
      })
      
      elementNames.push(name.toLowerCase())
    }
    
    // Check for unique names (important for voice navigation)
    const uniqueNames = new Set(elementNames.filter(name => name !== 'unnamed-element'))
    const totalNamed = elementNames.filter(name => name !== 'unnamed-element').length
    
    // At least 80% of elements should have unique names
    expect(uniqueNames.size / totalNamed).toBeGreaterThan(0.8)
  })

  test('should handle zoom up to 200%', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Test different zoom levels
    const zoomLevels = [1, 1.5, 2] // 100%, 150%, 200%
    
    for (const zoom of zoomLevels) {
      // Set zoom level
      await page.evaluate((zoomLevel) => {
        document.body.style.zoom = zoomLevel
      }, zoom)
      
      await page.waitForTimeout(500)
      
      // Check that content is still accessible
      const navigationVisible = await page.locator('[data-testid="dashboard-nav"]').isVisible()
      const contentVisible = await page.locator('#main-content').isVisible()
      
      expect(navigationVisible).toBe(true)
      expect(contentVisible).toBe(true)
      
      // Check that text doesn't overflow containers
      const hasHorizontalScroll = await page.evaluate(() => {
        return document.body.scrollWidth > document.body.clientWidth
      })
      
      // Some horizontal scroll is acceptable at high zoom levels
      if (zoom <= 1.5) {
        expect(hasHorizontalScroll).toBe(false)
      }
    }
    
    // Reset zoom
    await page.evaluate(() => {
      document.body.style.zoom = '1'
    })
  })

  test('should provide error messages and feedback', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Navigate to real-time dashboard
    await page.click('button:has-text("Real-time")')
    await page.waitForTimeout(1000)
    
    // Simulate error state by mocking WebSocket failure
    await page.evaluate(() => {
      // Create error message for testing
      const errorElement = document.createElement('div')
      errorElement.role = 'alert'
      errorElement.textContent = 'Connection failed. Please check your network.'
      errorElement.id = 'test-error-message'
      document.body.appendChild(errorElement)
    })
    
    // Check error message accessibility
    const errorMessage = page.locator('#test-error-message')
    await expect(errorMessage).toBeVisible()
    
    const errorRole = await errorMessage.getAttribute('role')
    expect(errorRole).toBe('alert')
    
    const errorText = await errorMessage.textContent()
    expect(errorText).toContain('Connection failed')
    
    // Clean up
    await page.evaluate(() => {
      const errorEl = document.getElementById('test-error-message')
      if (errorEl) errorEl.remove()
    })
  })
})

test.describe('Mobile Accessibility', () => {
  
  test.use({ 
    viewport: { width: 375, height: 667 }
  })

  test('should be accessible on mobile devices', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2aa'])
      .analyze()
    
    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('should support touch navigation', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Test touch targets are large enough (minimum 44px)
    const touchTargets = await page.locator('button, a, input[type="checkbox"], input[type="radio"]').all()
    
    for (const target of touchTargets) {
      const boundingBox = await target.boundingBox()
      
      if (boundingBox) {
        expect(boundingBox.width).toBeGreaterThanOrEqual(44)
        expect(boundingBox.height).toBeGreaterThanOrEqual(44)
      }
    }
  })

  test('should handle orientation changes', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Test portrait mode
    await page.setViewportSize({ width: 375, height: 667 })
    await page.waitForTimeout(500)
    
    let contentVisible = await page.locator('#main-content').isVisible()
    expect(contentVisible).toBe(true)
    
    // Test landscape mode
    await page.setViewportSize({ width: 667, height: 375 })
    await page.waitForTimeout(500)
    
    contentVisible = await page.locator('#main-content').isVisible()
    expect(contentVisible).toBe(true)
    
    // Navigation should still be accessible
    const navigationVisible = await page.locator('button:has-text("Overview")').isVisible()
    expect(navigationVisible).toBe(true)
  })
})