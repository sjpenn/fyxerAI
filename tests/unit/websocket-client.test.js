/**
 * Unit tests for WebSocket client functionality
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { JSDOM } from 'jsdom'

// Mock WebSocket implementation for detailed testing
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  constructor(url) {
    this.url = url
    this.readyState = MockWebSocket.CONNECTING
    this.onopen = null
    this.onclose = null
    this.onmessage = null
    this.onerror = null
    
    // Simulate connection opening
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      if (this.onopen) this.onopen(new Event('open'))
    }, 10)
  }

  send(data) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open')
    }
    this.lastSentMessage = data
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) this.onclose(new Event('close'))
  }

  // Test helper methods
  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) })
    }
  }

  simulateError(error) {
    if (this.onerror) {
      this.onerror({ error })
    }
  }

  simulateClose() {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) this.onclose(new Event('close'))
  }
}

// Load the WebSocket client code
async function loadWebSocketClient() {
  const fs = await import('fs')
  const path = await import('path')
  
  const clientCode = fs.readFileSync(
    path.resolve('./static/js/websocket-client.js'), 
    'utf-8'
  )
  
  // Remove the auto-execution parts for testing
  const testableCode = clientCode
    .replace(/document\.addEventListener\('DOMContentLoaded'.*?\}\);?/s, '')
    .replace(/window\.addEventListener\('beforeunload'.*?\}\);?/s, '')
  
  return testableCode
}

describe('EmailWebSocketClient', () => {
  let dom
  let window
  let document
  let EmailWebSocketClient
  let client

  beforeEach(async () => {
    // Setup JSDOM
    dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
      url: 'http://localhost:8000'
    })
    window = dom.window
    document = window.document
    
    // Add to global scope
    global.window = window
    global.document = document
    global.location = window.location
    
    // Mock WebSocket
    global.WebSocket = MockWebSocket
    window.WebSocket = MockWebSocket
    
    // Load and evaluate the client code
    const clientCode = await loadWebSocketClient()
    const script = document.createElement('script')
    script.textContent = clientCode
    document.head.appendChild(script)
    
    // Get the class from window
    EmailWebSocketClient = window.EmailWebSocketClient
    
    // Create client instance
    client = new EmailWebSocketClient()
  })

  afterEach(() => {
    if (client) {
      client.disconnect()
    }
    dom?.window?.close()
  })

  describe('Initialization', () => {
    it('should initialize with default properties', () => {
      expect(client.syncSocket).toBeNull()
      expect(client.notificationSocket).toBeNull()
      expect(client.isConnecting).toBe(false)
      expect(client.reconnectAttempts).toBe(0)
      expect(client.maxReconnectAttempts).toBe(5)
    })

    it('should initialize Alpine store if available', () => {
      expect(Alpine.store).toHaveBeenCalledWith('realtime', expect.any(Object))
    })
  })

  describe('Connection Management', () => {
    it('should connect both WebSocket types', async () => {
      await new Promise(resolve => {
        client.connect()
        setTimeout(() => {
          expect(client.syncSocket).toBeInstanceOf(MockWebSocket)
          expect(client.notificationSocket).toBeInstanceOf(MockWebSocket)
          expect(client.syncSocket.url).toContain('/ws/email-sync/')
          expect(client.notificationSocket.url).toContain('/ws/notifications/')
          resolve()
        }, 20)
      })
    })

    it('should handle connection failures gracefully', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      // Mock WebSocket constructor to throw error
      global.WebSocket = vi.fn(() => {
        throw new Error('Connection failed')
      })
      
      client.connect()
      
      expect(client.isConnecting).toBe(false)
      expect(consoleSpy).toHaveBeenCalled()
      
      consoleSpy.mockRestore()
    })

    it('should prevent multiple simultaneous connections', () => {
      client.isConnecting = true
      const originalConnect = client.connectSyncWebSocket
      client.connectSyncWebSocket = vi.fn()
      
      client.connect()
      
      expect(client.connectSyncWebSocket).not.toHaveBeenCalled()
    })
  })

  describe('Message Handling', () => {
    beforeEach(async () => {
      client.connect()
      await new Promise(resolve => setTimeout(resolve, 20))
    })

    it('should handle sync status messages', () => {
      const mockStore = Alpine.store('realtime')
      const statusData = {
        active_accounts: 2,
        total_accounts: 3,
        is_syncing: false
      }

      client.syncSocket.simulateMessage({
        type: 'sync_status',
        data: statusData
      })

      expect(mockStore.syncStatus).toEqual(expect.objectContaining(statusData))
    })

    it('should handle sync progress messages', () => {
      const mockStore = Alpine.store('realtime')
      
      client.syncSocket.simulateMessage({
        type: 'sync_started',
        accounts_count: 2
      })

      expect(mockStore.syncStatus.is_syncing).toBe(true)
    })

    it('should handle new email notifications', () => {
      const mockStore = Alpine.store('realtime')
      const emailData = {
        id: '123',
        subject: 'Test Email',
        sender: 'test@example.com',
        is_urgent: false
      }

      client.notificationSocket.simulateMessage({
        type: 'new_email_notification',
        data: emailData
      })

      expect(mockStore.recentEmails[0]).toEqual(emailData)
      expect(mockStore.unreadCount).toBe(1)
    })

    it('should handle urgent email alerts', () => {
      const showUrgentAlert = vi.fn()
      client.showUrgentAlert = showUrgentAlert
      
      const alertData = {
        id: '456',
        subject: 'URGENT: Server Down',
        sender: 'alerts@company.com',
        message: 'Critical alert'
      }

      client.notificationSocket.simulateMessage({
        type: 'urgent_alert',
        data: alertData
      })

      expect(showUrgentAlert).toHaveBeenCalledWith(alertData)
    })

    it('should handle error messages', () => {
      const showNotification = vi.fn()
      client.showNotification = showNotification

      client.syncSocket.simulateMessage({
        type: 'error',
        message: 'Test error message'
      })

      expect(showNotification).toHaveBeenCalledWith('Test error message', 'error')
    })
  })

  describe('Public API Methods', () => {
    beforeEach(async () => {
      client.connect()
      await new Promise(resolve => setTimeout(resolve, 20))
    })

    it('should send sync start message', () => {
      client.startSync(true)
      
      expect(client.syncSocket.lastSentMessage).toBe(JSON.stringify({
        type: 'start_sync',
        force_full_sync: true
      }))
    })

    it('should send mark read message', () => {
      const emailIds = ['123', '456']
      client.markEmailRead(emailIds)
      
      expect(client.syncSocket.lastSentMessage).toBe(JSON.stringify({
        type: 'mark_read',
        email_ids: emailIds
      }))
    })

    it('should request sync status', () => {
      client.getSyncStatus()
      
      expect(client.syncSocket.lastSentMessage).toBe(JSON.stringify({
        type: 'get_status'
      }))
    })

    it('should update notification preferences', () => {
      const preferences = { email_notifications: false }
      client.updateNotificationPreferences(preferences)
      
      expect(client.notificationSocket.lastSentMessage).toBe(JSON.stringify({
        type: 'update_preferences',
        preferences
      }))
    })
  })

  describe('Reconnection Logic', () => {
    it('should attempt reconnection on disconnect', async () => {
      client.connect()
      await new Promise(resolve => setTimeout(resolve, 20))
      
      const scheduleReconnect = vi.spyOn(client, 'scheduleReconnect')
      
      // Simulate disconnect
      client.syncSocket.simulateClose()
      
      expect(scheduleReconnect).toHaveBeenCalledWith('sync')
    })

    it('should implement exponential backoff', () => {
      const setTimeout = vi.spyOn(global, 'setTimeout')
      
      client.reconnectAttempts = 2
      client.scheduleReconnect('sync')
      
      // Should use exponential backoff: 1000 * 2^(2-1) = 2000ms
      expect(setTimeout).toHaveBeenCalledWith(expect.any(Function), 2000)
    })

    it('should stop reconnecting after max attempts', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      client.reconnectAttempts = client.maxReconnectAttempts
      client.scheduleReconnect('sync')
      
      expect(consoleError).toHaveBeenCalledWith(
        expect.stringContaining('Max reconnection attempts reached')
      )
      
      consoleError.mockRestore()
    })
  })

  describe('Notification System', () => {
    it('should show browser notifications when permitted', () => {
      global.Notification.permission = 'granted'
      
      client.showNotification('Test message', 'info')
      
      expect(global.Notification).toHaveBeenCalledWith(
        'FYXERAI Email Assistant',
        expect.objectContaining({
          body: 'Test message'
        })
      )
    })

    it('should play sound for urgent notifications', () => {
      const playNotificationSound = vi.spyOn(client, 'playNotificationSound')
      
      const emailData = { 
        sender: 'test@example.com',
        subject: 'Test',
        is_urgent: true
      }
      
      client.showEmailNotification(emailData)
      
      expect(playNotificationSound).toHaveBeenCalled()
    })

    it('should handle audio playback errors gracefully', () => {
      const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => {})
      
      global.Audio = vi.fn(() => ({
        play: vi.fn(() => Promise.reject(new Error('Audio failed')))
      }))
      
      client.playNotificationSound()
      
      expect(consoleLog).toHaveBeenCalled()
      consoleLog.mockRestore()
    })
  })

  describe('Error Handling', () => {
    it('should handle JSON parsing errors', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      client.connect()
      
      // Simulate invalid JSON
      if (client.syncSocket?.onmessage) {
        client.syncSocket.onmessage({ data: 'invalid json' })
      }
      
      expect(consoleError).toHaveBeenCalledWith(
        'Error parsing sync message:', 
        expect.any(Error)
      )
      
      consoleError.mockRestore()
    })

    it('should handle WebSocket errors', () => {
      const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      client.connect()
      
      const error = new Error('WebSocket error')
      client.syncSocket?.simulateError(error)
      
      expect(consoleError).toHaveBeenCalledWith('Sync WebSocket error:', error)
      consoleError.mockRestore()
    })

    it('should warn when trying to send on closed socket', () => {
      const consoleWarn = vi.spyOn(console, 'warn').mockImplementation(() => {})
      
      client.syncSocket = { readyState: MockWebSocket.CLOSED }
      client.startSync()
      
      expect(consoleWarn).toHaveBeenCalledWith('Sync WebSocket not connected')
      consoleWarn.mockRestore()
    })
  })

  describe('Static Methods', () => {
    it('should request notification permission', async () => {
      global.Notification.requestPermission.mockResolvedValue('granted')
      
      const result = await EmailWebSocketClient.requestNotificationPermission()
      
      expect(result).toBe(true)
      expect(global.Notification.requestPermission).toHaveBeenCalled()
    })

    it('should handle notification permission denial', async () => {
      global.Notification.requestPermission.mockResolvedValue('denied')
      
      const result = await EmailWebSocketClient.requestNotificationPermission()
      
      expect(result).toBe(false)
    })

    it('should handle browsers without Notification API', async () => {
      delete global.Notification
      
      const result = await EmailWebSocketClient.requestNotificationPermission()
      
      expect(result).toBe(false)
    })
  })
})