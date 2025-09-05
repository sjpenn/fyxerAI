/**
 * Performance tests for FYXERAI application
 */

import { test, expect } from '@playwright/test'

test.describe('Performance Tests', () => {
  
  test('should meet Core Web Vitals thresholds', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Measure Core Web Vitals
    const vitals = await page.evaluate(() => {
      return new Promise((resolve) => {
        const vitals = {}
        
        // Largest Contentful Paint (LCP)
        new PerformanceObserver((list) => {
          const entries = list.getEntries()
          const lastEntry = entries[entries.length - 1]
          vitals.lcp = lastEntry.startTime
        }).observe({ entryTypes: ['largest-contentful-paint'] })
        
        // First Input Delay (FID) - approximated with First Contentful Paint
        new PerformanceObserver((list) => {
          const entries = list.getEntries()
          const fcpEntry = entries.find(entry => entry.name === 'first-contentful-paint')
          if (fcpEntry) {
            vitals.fcp = fcpEntry.startTime
          }
        }).observe({ entryTypes: ['paint'] })
        
        // Cumulative Layout Shift (CLS)
        let clsValue = 0
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!entry.hadRecentInput) {
              clsValue += entry.value
            }
          }
          vitals.cls = clsValue
        }).observe({ entryTypes: ['layout-shift'] })
        
        // Give some time for measurements
        setTimeout(() => {
          vitals.navigationTiming = performance.getEntriesByType('navigation')[0]
          resolve(vitals)
        }, 3000)
      })
    })
    
    // Assert Core Web Vitals thresholds
    if (vitals.lcp) {
      expect(vitals.lcp).toBeLessThan(2500) // LCP should be < 2.5s
    }
    
    if (vitals.cls) {
      expect(vitals.cls).toBeLessThan(0.1) // CLS should be < 0.1
    }
    
    if (vitals.navigationTiming) {
      const { domContentLoadedEventEnd, navigationStart } = vitals.navigationTiming
      const dcl = domContentLoadedEventEnd - navigationStart
      expect(dcl).toBeLessThan(1500) // DOM Content Loaded < 1.5s
    }
  })

  test('should load dashboard within performance budget', async ({ page }) => {
    const startTime = Date.now()
    
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    
    const dclTime = Date.now() - startTime
    
    await page.waitForLoadState('networkidle')
    
    const totalLoadTime = Date.now() - startTime
    
    // Performance budgets
    expect(dclTime).toBeLessThan(1000) // DOM ready within 1s
    expect(totalLoadTime).toBeLessThan(3000) // Complete load within 3s
  })

  test('should handle real-time updates efficiently', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Navigate to real-time dashboard
    await page.click('button:has-text("Real-time")')
    await page.waitForLoadState('networkidle')
    
    // Measure performance of rapid updates
    const updatePerformance = await page.evaluate(() => {
      return new Promise((resolve) => {
        const measurements = []
        const updateCount = 100
        let completedUpdates = 0
        
        // Simulate rapid DOM updates (like real-time notifications)
        const container = document.createElement('div')
        container.id = 'performance-test-container'
        document.body.appendChild(container)
        
        function performUpdate() {
          const start = performance.now()
          
          // Simulate notification update
          const notification = document.createElement('div')
          notification.className = 'notification-item'
          notification.textContent = `Update ${completedUpdates + 1}`
          container.appendChild(notification)
          
          // Remove old notifications to prevent memory buildup
          if (container.children.length > 10) {
            container.removeChild(container.firstChild)
          }
          
          const end = performance.now()
          measurements.push(end - start)
          
          completedUpdates++
          
          if (completedUpdates < updateCount) {
            setTimeout(performUpdate, 10) // 10ms intervals
          } else {
            // Clean up
            document.body.removeChild(container)
            
            resolve({
              averageUpdateTime: measurements.reduce((a, b) => a + b, 0) / measurements.length,
              maxUpdateTime: Math.max(...measurements),
              minUpdateTime: Math.min(...measurements),
              totalUpdates: completedUpdates
            })
          }
        }
        
        performUpdate()
      })
    })
    
    // Assert performance metrics
    expect(updatePerformance.averageUpdateTime).toBeLessThan(5) // Average update < 5ms
    expect(updatePerformance.maxUpdateTime).toBeLessThan(16) // Max update < 16ms (60fps)
    expect(updatePerformance.totalUpdates).toBe(100)
  })

  test('should handle large data sets efficiently', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Test rendering performance with large email lists
    const renderingPerformance = await page.evaluate(() => {
      return new Promise((resolve) => {
        const startTime = performance.now()
        
        // Create large email list
        const emailList = document.createElement('div')
        emailList.className = 'large-email-list'
        
        const emailCount = 1000
        const fragment = document.createDocumentFragment()
        
        for (let i = 0; i < emailCount; i++) {
          const emailItem = document.createElement('div')
          emailItem.className = 'email-item'
          emailItem.innerHTML = `
            <div class="email-subject">Email Subject ${i}</div>
            <div class="email-sender">sender${i}@example.com</div>
            <div class="email-preview">This is email preview text ${i}...</div>
          `
          fragment.appendChild(emailItem)
        }
        
        emailList.appendChild(fragment)
        document.body.appendChild(emailList)
        
        const renderTime = performance.now() - startTime
        
        // Clean up
        document.body.removeChild(emailList)
        
        resolve({
          renderTime,
          emailsRendered: emailCount,
          averageTimePerEmail: renderTime / emailCount
        })
      })
    })
    
    expect(renderingPerformance.renderTime).toBeLessThan(500) // Render 1000 items < 500ms
    expect(renderingPerformance.averageTimePerEmail).toBeLessThan(1) // < 1ms per email
  })

  test('should optimize WebSocket message processing', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Mock WebSocket for performance testing
    const messageProcessingPerformance = await page.evaluate(() => {
      return new Promise((resolve) => {
        // Mock WebSocket message processing
        const messageCount = 1000
        const messages = []
        const processingTimes = []
        
        // Generate test messages
        for (let i = 0; i < messageCount; i++) {
          messages.push({
            type: 'new_email_notification',
            data: {
              id: `email_${i}`,
              subject: `Test Email ${i}`,
              sender: `sender${i}@example.com`,
              received_at: new Date().toISOString()
            }
          })
        }
        
        // Process messages
        let processedCount = 0
        
        function processMessage(message) {
          const start = performance.now()
          
          // Simulate message processing (parsing, state update, DOM update)
          const data = JSON.parse(JSON.stringify(message))
          
          // Simulate Alpine.js store update
          if (window.Alpine && window.Alpine.store) {
            // Mock store update
            const mockUpdate = { ...data }
            mockUpdate.processed = true
          }
          
          const end = performance.now()
          processingTimes.push(end - start)
          
          processedCount++
          
          if (processedCount < messages.length) {
            // Process next message
            setTimeout(() => processMessage(messages[processedCount]), 1)
          } else {
            resolve({
              totalMessages: processedCount,
              averageProcessingTime: processingTimes.reduce((a, b) => a + b, 0) / processingTimes.length,
              maxProcessingTime: Math.max(...processingTimes),
              throughput: processedCount / (processingTimes.reduce((a, b) => a + b, 0) / 1000) // messages per second
            })
          }
        }
        
        processMessage(messages[0])
      })
    })
    
    expect(messageProcessingPerformance.averageProcessingTime).toBeLessThan(2) // < 2ms per message
    expect(messageProcessingPerformance.throughput).toBeGreaterThan(100) // > 100 messages/sec
  })

  test('should optimize memory usage', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    const memoryUsage = await page.evaluate(() => {
      const initialMemory = performance.memory ? {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      } : null
      
      // Simulate memory-intensive operations
      const largeArrays = []
      
      // Create and destroy large objects
      for (let i = 0; i < 100; i++) {
        const largeArray = new Array(10000).fill(`data-${i}`)
        largeArrays.push(largeArray)
        
        // Periodically clean up to test garbage collection
        if (i % 20 === 0) {
          largeArrays.splice(0, 10)
        }
      }
      
      // Force garbage collection hint
      if (window.gc) {
        window.gc()
      }
      
      const finalMemory = performance.memory ? {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      } : null
      
      return {
        initialMemory,
        finalMemory,
        memoryIncrease: finalMemory && initialMemory ? 
          finalMemory.used - initialMemory.used : null
      }
    })
    
    if (memoryUsage.memoryIncrease !== null) {
      // Memory increase should be reasonable (< 20MB for test operations)
      expect(memoryUsage.memoryIncrease).toBeLessThan(20 * 1024 * 1024)
    }
  })

  test('should handle concurrent operations efficiently', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Test concurrent tab switching and real-time updates
    const concurrentPerformance = await page.evaluate(() => {
      return new Promise((resolve) => {
        const operations = []
        const startTime = performance.now()
        
        // Simulate concurrent operations
        const promises = []
        
        // Concurrent DOM updates
        for (let i = 0; i < 50; i++) {
          promises.push(new Promise((resolve) => {
            setTimeout(() => {
              const element = document.createElement('div')
              element.textContent = `Concurrent operation ${i}`
              document.body.appendChild(element)
              
              setTimeout(() => {
                document.body.removeChild(element)
                resolve()
              }, 10)
            }, Math.random() * 100)
          }))
        }
        
        Promise.all(promises).then(() => {
          const endTime = performance.now()
          
          resolve({
            totalTime: endTime - startTime,
            operationsCompleted: promises.length,
            averageTimePerOperation: (endTime - startTime) / promises.length
          })
        })
      })
    })
    
    expect(concurrentPerformance.totalTime).toBeLessThan(1000) // All operations < 1s
    expect(concurrentPerformance.averageTimePerOperation).toBeLessThan(50) // < 50ms per operation
  })

  test('should maintain performance during long sessions', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Simulate extended usage
    const sessionPerformance = await page.evaluate(() => {
      return new Promise((resolve) => {
        const measurements = []
        const sessionDuration = 30000 // 30 seconds simulation
        const measurementInterval = 1000 // Measure every second
        
        let measurementCount = 0
        const maxMeasurements = sessionDuration / measurementInterval
        
        const measurePerformance = () => {
          const start = performance.now()
          
          // Simulate typical user interactions
          // Navigate between sections
          const buttons = document.querySelectorAll('button')
          if (buttons.length > 0) {
            const randomButton = buttons[Math.floor(Math.random() * buttons.length)]
            if (randomButton && randomButton.textContent !== 'Theme Toggle') {
              randomButton.click()
            }
          }
          
          // Simulate data updates
          const updateElements = document.querySelectorAll('.unread-count, .sync-status')
          updateElements.forEach(element => {
            if (element) {
              element.textContent = Math.floor(Math.random() * 100).toString()
            }
          })
          
          const end = performance.now()
          measurements.push(end - start)
          
          measurementCount++
          
          if (measurementCount < maxMeasurements) {
            setTimeout(measurePerformance, measurementInterval)
          } else {
            resolve({
              measurements,
              averageInteractionTime: measurements.reduce((a, b) => a + b, 0) / measurements.length,
              maxInteractionTime: Math.max(...measurements),
              performanceDegradation: measurements[measurements.length - 1] - measurements[0]
            })
          }
        }
        
        measurePerformance()
      })
    })
    
    expect(sessionPerformance.averageInteractionTime).toBeLessThan(10) // < 10ms average
    expect(sessionPerformance.maxInteractionTime).toBeLessThan(50) // < 50ms max
    expect(Math.abs(sessionPerformance.performanceDegradation)).toBeLessThan(20) // < 20ms degradation
  })
})

test.describe('Network Performance', () => {
  
  test('should handle slow network conditions', async ({ page, context }) => {
    // Simulate slow 3G network
    await context.route('**/*', route => {
      setTimeout(() => route.continue(), 100) // Add 100ms delay
    })
    
    const startTime = Date.now()
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    const loadTime = Date.now() - startTime
    
    // Should still load within reasonable time even with network delay
    expect(loadTime).toBeLessThan(5000)
  })

  test('should optimize resource loading', async ({ page }) => {
    const resourceMetrics = []
    
    page.on('response', response => {
      const timing = response.timing()
      resourceMetrics.push({
        url: response.url(),
        status: response.status(),
        size: response.headers()['content-length'] || 0,
        timing: timing
      })
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Analyze resource loading
    const cssFiles = resourceMetrics.filter(r => r.url.includes('.css'))
    const jsFiles = resourceMetrics.filter(r => r.url.includes('.js'))
    
    // CSS should load quickly
    cssFiles.forEach(file => {
      if (file.timing) {
        expect(file.timing.responseEnd - file.timing.requestStart).toBeLessThan(1000)
      }
    })
    
    // JavaScript files should be reasonably sized
    jsFiles.forEach(file => {
      if (file.size > 0) {
        expect(parseInt(file.size)).toBeLessThan(500 * 1024) // < 500KB per JS file
      }
    })
  })

  test('should handle API request batching', async ({ page }) => {
    let apiRequestCount = 0
    
    await page.route('/api/**', route => {
      apiRequestCount++
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true, data: [] })
      })
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Navigate through different tabs
    const tabs = ['Inbox', 'Accounts', 'Statistics']
    for (const tab of tabs) {
      await page.click(`button:has-text("${tab}")`)
      await page.waitForTimeout(500)
    }
    
    // Should not make excessive API requests
    expect(apiRequestCount).toBeLessThan(10) // Reasonable number of API calls
  })
})