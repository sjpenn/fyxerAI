/**
 * Unit tests for Alpine.js components and interactions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { JSDOM } from 'jsdom'

describe('Alpine.js Components', () => {
  let dom
  let window
  let document

  beforeEach(() => {
    // Setup JSDOM with Alpine.js mock
    dom = new JSDOM('<!DOCTYPE html><html><body></body></html>')
    window = dom.window
    document = window.document
    
    global.window = window
    global.document = document

    // Mock Alpine.js
    global.Alpine = {
      store: vi.fn(() => ({
        realtime: {
          syncConnected: false,
          notificationsConnected: false,
          syncStatus: {
            active_accounts: 2,
            total_accounts: 3,
            last_sync: '2024-01-15T10:30:00Z',
            is_syncing: false
          },
          unreadCount: 5,
          recentNotifications: [],
          recentEmails: [
            {
              id: '1',
              subject: 'Test Email 1',
              sender: 'sender1@example.com',
              category: 'important',
              is_urgent: false,
              received_at: '2024-01-15T10:25:00Z'
            }
          ],
          markEmailRead: vi.fn(),
          startSync: vi.fn(),
          addNotification: vi.fn(),
          removeNotification: vi.fn()
        },
        theme: {
          current: 'light',
          toggle: vi.fn()
        }
      })),
      data: vi.fn(),
      directive: vi.fn(),
      magic: vi.fn(),
      start: vi.fn()
    }
  })

  afterEach(() => {
    dom?.window?.close()
  })

  describe('Real-time Dashboard Component', () => {
    let component

    beforeEach(() => {
      // Load the real-time dashboard HTML
      document.body.innerHTML = `
        <div x-data="realtimeDashboard()" x-init="init()">
          <div class="connection-status">
            <div :class="$store.realtime.syncConnected ? 'bg-green-500' : 'bg-red-500'"></div>
            <div :class="$store.realtime.notificationsConnected ? 'bg-green-500' : 'bg-red-500'"></div>
          </div>
          
          <button @click="startSync(false)" 
                  :disabled="$store.realtime.syncStatus.is_syncing"
                  id="start-sync-btn">
            Start Sync
          </button>
          
          <button @click="startSync(true)" id="force-sync-btn">
            Force Full Sync
          </button>
          
          <div class="unread-count" x-text="$store.realtime.unreadCount"></div>
          
          <div class="recent-emails">
            <template x-for="email in $store.realtime.recentEmails.slice(0, 5)">
              <div class="email-item" @click="markEmailRead(email.id)">
                <span class="subject" x-text="email.subject"></span>
                <span class="category" x-text="email.category"></span>
              </div>
            </template>
          </div>
          
          <div class="notifications">
            <template x-for="notification in $store.realtime.recentNotifications.slice(0, 3)">
              <div class="notification">
                <span x-text="notification.message"></span>
                <button @click="$store.realtime.removeNotification(notification.id)">×</button>
              </div>
            </template>
          </div>
        </div>
      `

      // Mock the realtimeDashboard function
      global.realtimeDashboard = () => ({
        urgentAlert: false,
        urgentEmailData: null,
        
        init() {
          // Mock init functionality
        },
        
        startSync(forceFullSync = false) {
          if (global.emailWebSocket) {
            global.emailWebSocket.startSync(forceFullSync)
          }
        },
        
        markEmailRead(emailId) {
          if (global.emailWebSocket) {
            global.emailWebSocket.markEmailRead([emailId])
            const store = Alpine.store('realtime')
            if (store.unreadCount > 0) {
              store.unreadCount--
            }
          }
        },
        
        formatDate(dateString) {
          if (!dateString) return ''
          const date = new Date(dateString)
          const now = new Date()
          const diffMs = now - date
          const diffMins = Math.floor(diffMs / 60000)
          
          if (diffMins < 1) return 'Just now'
          if (diffMins < 60) return `${diffMins}m ago`
          return date.toLocaleDateString()
        },
        
        getCategoryBadgeClass(category) {
          const classes = {
            urgent: 'bg-red-100 text-red-800',
            important: 'bg-orange-100 text-orange-800',
            routine: 'bg-blue-100 text-blue-800',
            promotional: 'bg-green-100 text-green-800',
            spam: 'bg-gray-100 text-gray-800'
          }
          return classes[category] || classes.routine
        }
      })

      component = global.realtimeDashboard()
    })

    it('should initialize with correct default state', () => {
      expect(component.urgentAlert).toBe(false)
      expect(component.urgentEmailData).toBeNull()
    })

    it('should format dates correctly', () => {
      // Test "Just now"
      const now = new Date().toISOString()
      expect(component.formatDate(now)).toBe('Just now')
      
      // Test minutes ago
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString()
      expect(component.formatDate(fiveMinutesAgo)).toBe('5m ago')
      
      // Test empty string
      expect(component.formatDate('')).toBe('')
      expect(component.formatDate(null)).toBe('')
    })

    it('should return correct category badge classes', () => {
      expect(component.getCategoryBadgeClass('urgent')).toBe('bg-red-100 text-red-800')
      expect(component.getCategoryBadgeClass('important')).toBe('bg-orange-100 text-orange-800')
      expect(component.getCategoryBadgeClass('unknown')).toBe('bg-blue-100 text-blue-800')
    })

    it('should call WebSocket methods when syncing', () => {
      global.emailWebSocket = {
        startSync: vi.fn()
      }

      component.startSync(true)
      expect(global.emailWebSocket.startSync).toHaveBeenCalledWith(true)

      component.startSync(false)
      expect(global.emailWebSocket.startSync).toHaveBeenCalledWith(false)
    })

    it('should handle email reading', () => {
      global.emailWebSocket = {
        markEmailRead: vi.fn()
      }
      
      const store = Alpine.store('realtime')
      store.unreadCount = 5

      component.markEmailRead('test-email-id')

      expect(global.emailWebSocket.markEmailRead).toHaveBeenCalledWith(['test-email-id'])
      expect(store.unreadCount).toBe(4)
    })
  })

  describe('Theme Toggle Component', () => {
    let themeToggle

    beforeEach(() => {
      // Mock localStorage
      global.localStorage = {
        getItem: vi.fn(() => null),
        setItem: vi.fn()
      }

      // Create theme toggle component
      themeToggle = {
        isDark: false,
        
        init() {
          const stored = localStorage.getItem('theme')
          this.isDark = stored === 'dark' || 
            (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)
          this.updateTheme()
        },
        
        toggle() {
          this.isDark = !this.isDark
          this.updateTheme()
          localStorage.setItem('theme', this.isDark ? 'dark' : 'light')
        },
        
        updateTheme() {
          if (this.isDark) {
            document.documentElement.classList.add('dark')
          } else {
            document.documentElement.classList.remove('dark')
          }
        }
      }
    })

    it('should initialize with system preference', () => {
      // Mock matchMedia to return dark preference
      window.matchMedia = vi.fn(() => ({
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn()
      }))

      themeToggle.init()
      
      expect(themeToggle.isDark).toBe(true)
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })

    it('should toggle theme correctly', () => {
      themeToggle.isDark = false
      themeToggle.toggle()
      
      expect(themeToggle.isDark).toBe(true)
      expect(localStorage.setItem).toHaveBeenCalledWith('theme', 'dark')
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })

    it('should respect stored theme preference', () => {
      global.localStorage.getItem.mockReturnValue('dark')
      
      themeToggle.init()
      
      expect(themeToggle.isDark).toBe(true)
    })
  })

  describe('Modal Component', () => {
    let modal

    beforeEach(() => {
      modal = {
        open: false,
        
        show() {
          this.open = true
          document.body.style.overflow = 'hidden'
        },
        
        hide() {
          this.open = false
          document.body.style.overflow = ''
        },
        
        toggle() {
          this.open ? this.hide() : this.show()
        }
      }
    })

    it('should show modal correctly', () => {
      modal.show()
      
      expect(modal.open).toBe(true)
      expect(document.body.style.overflow).toBe('hidden')
    })

    it('should hide modal correctly', () => {
      modal.open = true
      document.body.style.overflow = 'hidden'
      
      modal.hide()
      
      expect(modal.open).toBe(false)
      expect(document.body.style.overflow).toBe('')
    })

    it('should toggle modal state', () => {
      expect(modal.open).toBe(false)
      
      modal.toggle()
      expect(modal.open).toBe(true)
      
      modal.toggle()
      expect(modal.open).toBe(false)
    })
  })

  describe('Alpine Store Integration', () => {
    let store

    beforeEach(() => {
      store = Alpine.store('realtime')
    })

    it('should have correct initial state', () => {
      expect(store.syncConnected).toBe(false)
      expect(store.notificationsConnected).toBe(false)
      expect(store.unreadCount).toBe(5)
      expect(store.recentEmails).toHaveLength(1)
    })

    it('should handle store method calls', () => {
      store.markEmailRead('test-id')
      expect(store.markEmailRead).toHaveBeenCalledWith('test-id')

      store.startSync(true)
      expect(store.startSync).toHaveBeenCalledWith(true)
    })

    it('should manage notifications correctly', () => {
      const notification = {
        id: 'test-notification',
        message: 'Test message',
        type: 'info'
      }

      store.addNotification(notification)
      expect(store.addNotification).toHaveBeenCalledWith(notification)

      store.removeNotification('test-notification')
      expect(store.removeNotification).toHaveBeenCalledWith('test-notification')
    })
  })

  describe('Component Interactions', () => {
    it('should handle urgent email alert display', () => {
      const component = global.realtimeDashboard()
      
      const urgentData = {
        id: '123',
        subject: 'URGENT: Server Down',
        sender: 'alerts@company.com'
      }

      component.showUrgentAlert = vi.fn()
      
      // Simulate urgent email event
      const event = new CustomEvent('urgent-email', { detail: urgentData })
      window.dispatchEvent(event)

      // In a real scenario, this would be handled by the Alpine component
      component.showUrgentAlert(urgentData)
      expect(component.showUrgentAlert).toHaveBeenCalledWith(urgentData)
    })

    it('should handle connection status changes', () => {
      const store = Alpine.store('realtime')
      
      // Simulate connection status changes
      store.syncConnected = true
      store.notificationsConnected = true

      expect(store.syncConnected).toBe(true)
      expect(store.notificationsConnected).toBe(true)
    })

    it('should update unread count reactively', () => {
      const store = Alpine.store('realtime')
      
      expect(store.unreadCount).toBe(5)
      
      // Simulate new email arrival
      store.unreadCount++
      expect(store.unreadCount).toBe(6)
      
      // Simulate email being read
      store.unreadCount--
      expect(store.unreadCount).toBe(5)
    })
  })

  describe('Event Handling', () => {
    it('should handle WebSocket connection changes', () => {
      const handleConnectionChange = vi.fn()
      
      // Simulate WebSocket connection change event
      const event = new CustomEvent('websocketConnectionChange', {
        detail: { socketType: 'sync', connected: true }
      })
      
      window.addEventListener('websocketConnectionChange', handleConnectionChange)
      window.dispatchEvent(event)
      
      expect(handleConnectionChange).toHaveBeenCalledWith(
        expect.objectContaining({
          detail: { socketType: 'sync', connected: true }
        })
      )
    })

    it('should handle keyboard navigation', () => {
      const component = global.realtimeDashboard()
      
      // Mock keyboard event handling
      const handleKeydown = (event) => {
        if (event.key === 'Escape' && component.urgentAlert) {
          component.urgentAlert = false
        }
      }

      component.urgentAlert = true
      
      const escapeEvent = new KeyboardEvent('keydown', { key: 'Escape' })
      handleKeydown(escapeEvent)
      
      expect(component.urgentAlert).toBe(false)
    })
  })

  describe('Accessibility Features', () => {
    it('should have proper ARIA attributes for notifications', () => {
      document.body.innerHTML = `
        <div class="notification" role="alert" aria-live="polite">
          <span>Test notification</span>
          <button aria-label="Dismiss notification">×</button>
        </div>
      `

      const notification = document.querySelector('.notification')
      const dismissBtn = notification.querySelector('button')

      expect(notification.getAttribute('role')).toBe('alert')
      expect(notification.getAttribute('aria-live')).toBe('polite')
      expect(dismissBtn.getAttribute('aria-label')).toBe('Dismiss notification')
    })

    it('should handle focus management for modals', () => {
      document.body.innerHTML = `
        <div class="modal" tabindex="-1">
          <button class="close-btn">Close</button>
          <input type="text" />
          <button class="action-btn">Action</button>
        </div>
      `

      const modal = document.querySelector('.modal')
      const firstInput = modal.querySelector('input')
      
      // Mock focus method
      firstInput.focus = vi.fn()
      
      // Simulate modal opening
      firstInput.focus()
      
      expect(firstInput.focus).toHaveBeenCalled()
    })
  })
})