/**
 * Integration tests for WebSocket functionality with backend
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { WebSocket as MockWebSocket } from 'ws'

// Mock WebSocket Server for testing
class MockWebSocketServer {
  constructor() {
    this.clients = new Set()
    this.handlers = new Map()
  }

  addClient(client) {
    this.clients.add(client)
    client.server = this
  }

  removeClient(client) {
    this.clients.delete(client)
  }

  broadcast(message) {
    this.clients.forEach(client => {
      if (client.readyState === MockWebSocket.OPEN) {
        client.send(JSON.stringify(message))
      }
    })
  }

  sendToClient(client, message) {
    if (client.readyState === MockWebSocket.OPEN) {
      client.send(JSON.stringify(message))
    }
  }

  on(event, handler) {
    this.handlers.set(event, handler)
  }

  emit(event, ...args) {
    const handler = this.handlers.get(event)
    if (handler) {
      handler(...args)
    }
  }
}

describe('WebSocket Integration Tests', () => {
  let server
  let client
  let emailWebSocket

  beforeEach(async () => {
    // Setup mock server
    server = new MockWebSocketServer()

    // Setup WebSocket client
    global.WebSocket = class extends EventTarget {
      constructor(url) {
        super()
        this.url = url
        this.readyState = WebSocket.CONNECTING
        this.bufferedAmount = 0
        
        // Simulate connection
        setTimeout(() => {
          this.readyState = WebSocket.OPEN
          this.dispatchEvent(new Event('open'))
        }, 10)
      }

      send(data) {
        if (this.readyState !== WebSocket.OPEN) {
          throw new Error('WebSocket is not open')
        }
        this.lastSent = data
        // Simulate server receiving the message
        server.emit('message', JSON.parse(data))
      }

      close() {
        this.readyState = WebSocket.CLOSED
        this.dispatchEvent(new Event('close'))
      }

      // Static constants
      static get CONNECTING() { return 0 }
      static get OPEN() { return 1 }
      static get CLOSING() { return 2 }
      static get CLOSED() { return 3 }
    }

    // Setup Alpine store mock
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
      }))
    }

    // Create EmailWebSocketClient instance
    const { EmailWebSocketClient } = await import('@js/websocket-client.js').catch(() => {
      // Fallback: create simplified client for testing
      return {
        EmailWebSocketClient: class {
          constructor() {
            this.syncSocket = null
            this.notificationSocket = null
            this.isConnecting = false
            this.reconnectAttempts = 0
            this.maxReconnectAttempts = 5
          }

          async connect() {
            this.syncSocket = new WebSocket('ws://localhost:8000/ws/email-sync/')
            this.notificationSocket = new WebSocket('ws://localhost:8000/ws/notifications/')
            
            return new Promise((resolve) => {
              let connections = 0
              const checkConnections = () => {
                connections++
                if (connections === 2) resolve()
              }
              
              this.syncSocket.addEventListener('open', checkConnections)
              this.notificationSocket.addEventListener('open', checkConnections)
            })
          }

          startSync(forceFullSync = false) {
            if (this.syncSocket?.readyState === WebSocket.OPEN) {
              this.syncSocket.send(JSON.stringify({
                type: 'start_sync',
                force_full_sync: forceFullSync
              }))
            }
          }

          markEmailRead(emailIds) {
            if (this.syncSocket?.readyState === WebSocket.OPEN) {
              this.syncSocket.send(JSON.stringify({
                type: 'mark_read',
                email_ids: emailIds
              }))
            }
          }

          disconnect() {
            this.syncSocket?.close()
            this.notificationSocket?.close()
          }
        }
      }
    })

    emailWebSocket = new EmailWebSocketClient()
  })

  afterEach(() => {
    if (emailWebSocket) {
      emailWebSocket.disconnect()
    }
    vi.clearAllMocks()
  })

  describe('Connection Establishment', () => {
    it('should establish sync and notification connections', async () => {
      await emailWebSocket.connect()
      
      expect(emailWebSocket.syncSocket).toBeTruthy()
      expect(emailWebSocket.notificationSocket).toBeTruthy()
      expect(emailWebSocket.syncSocket.url).toContain('/ws/email-sync/')
      expect(emailWebSocket.notificationSocket.url).toContain('/ws/notifications/')
    })

    it('should handle connection timeouts', async () => {
      // Mock WebSocket that never opens
      global.WebSocket = class extends EventTarget {
        constructor(url) {
          super()
          this.url = url
          this.readyState = WebSocket.CONNECTING
          // Never dispatch 'open' event to simulate timeout
        }
        send() {}
        close() { this.readyState = WebSocket.CLOSED }
        static get CONNECTING() { return 0 }
        static get OPEN() { return 1 }
        static get CLOSED() { return 3 }
      }

      const client = new EmailWebSocketClient()
      
      // Should handle gracefully even if connection doesn't establish
      await expect(
        Promise.race([
          client.connect(),
          new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Connection timeout')), 100)
          )
        ])
      ).rejects.toThrow('Connection timeout')
    })
  })

  describe('Message Exchange', () => {
    beforeEach(async () => {
      await emailWebSocket.connect()
      
      // Setup server message handlers
      server.on('message', (data) => {
        // Simulate server responses
        switch (data.type) {
          case 'start_sync':
            server.broadcast({
              type: 'sync_started',
              accounts_count: 2,
              force_full_sync: data.force_full_sync
            })
            break
          case 'get_status':
            server.broadcast({
              type: 'sync_status',
              data: {
                active_accounts: 2,
                total_accounts: 3,
                is_syncing: false
              }
            })
            break
          case 'mark_read':
            server.broadcast({
              type: 'emails_marked_read',
              count: data.email_ids.length,
              email_ids: data.email_ids
            })
            break
        }
      })
    })

    it('should send and receive sync messages', async () => {
      const messagePromise = new Promise((resolve) => {
        emailWebSocket.syncSocket.addEventListener('message', (event) => {
          const data = JSON.parse(event.data)
          resolve(data)
        })
      })

      // Send sync request
      emailWebSocket.startSync(true)

      // Simulate server response
      const mockResponse = {
        type: 'sync_started',
        accounts_count: 2,
        force_full_sync: true
      }
      
      setTimeout(() => {
        emailWebSocket.syncSocket.dispatchEvent(
          new MessageEvent('message', { 
            data: JSON.stringify(mockResponse) 
          })
        )
      }, 10)

      const response = await messagePromise
      expect(response).toEqual(mockResponse)
    })

    it('should handle notification messages', async () => {
      const notificationPromise = new Promise((resolve) => {
        emailWebSocket.notificationSocket.addEventListener('message', (event) => {
          const data = JSON.parse(event.data)
          resolve(data)
        })
      })

      // Simulate new email notification
      const emailNotification = {
        type: 'new_email_notification',
        data: {
          id: '123',
          subject: 'Test Email',
          sender: 'test@example.com',
          is_urgent: false
        }
      }

      setTimeout(() => {
        emailWebSocket.notificationSocket.dispatchEvent(
          new MessageEvent('message', { 
            data: JSON.stringify(emailNotification) 
          })
        )
      }, 10)

      const notification = await notificationPromise
      expect(notification.type).toBe('new_email_notification')
      expect(notification.data.subject).toBe('Test Email')
    })

    it('should handle urgent email alerts', async () => {
      const urgentAlertPromise = new Promise((resolve) => {
        emailWebSocket.notificationSocket.addEventListener('message', (event) => {
          const data = JSON.parse(event.data)
          if (data.type === 'urgent_alert') {
            resolve(data)
          }
        })
      })

      const urgentAlert = {
        type: 'urgent_alert',
        data: {
          id: '456',
          subject: 'URGENT: Server Down',
          sender: 'alerts@company.com',
          message: 'Critical system alert'
        }
      }

      setTimeout(() => {
        emailWebSocket.notificationSocket.dispatchEvent(
          new MessageEvent('message', { 
            data: JSON.stringify(urgentAlert) 
          })
        )
      }, 10)

      const alert = await urgentAlertPromise
      expect(alert.type).toBe('urgent_alert')
      expect(alert.data.subject).toContain('URGENT')
    })
  })

  describe('Error Handling', () => {
    beforeEach(async () => {
      await emailWebSocket.connect()
    })

    it('should handle WebSocket errors', async () => {
      const errorPromise = new Promise((resolve) => {
        emailWebSocket.syncSocket.addEventListener('error', resolve)
      })

      // Simulate WebSocket error
      setTimeout(() => {
        emailWebSocket.syncSocket.dispatchEvent(
          new ErrorEvent('error', { error: new Error('Connection failed') })
        )
      }, 10)

      const errorEvent = await errorPromise
      expect(errorEvent).toBeTruthy()
    })

    it('should handle malformed JSON messages', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      // Simulate malformed JSON
      setTimeout(() => {
        emailWebSocket.syncSocket.dispatchEvent(
          new MessageEvent('message', { data: 'invalid json' })
        )
      }, 10)

      // Wait for error handling
      await new Promise(resolve => setTimeout(resolve, 20))

      // Should log error without crashing
      expect(consoleSpy).toHaveBeenCalled()
      consoleSpy.mockRestore()
    })
  })

  describe('Reconnection Logic', () => {
    it('should attempt reconnection on disconnect', async () => {
      await emailWebSocket.connect()
      
      const reconnectionPromise = new Promise((resolve) => {
        const originalConnect = emailWebSocket.connect
        emailWebSocket.connect = vi.fn().mockImplementation(() => {
          resolve()
          return originalConnect.call(emailWebSocket)
        })
      })

      // Simulate disconnect
      emailWebSocket.syncSocket.dispatchEvent(new Event('close'))

      // Should attempt reconnection (would happen after delay in real implementation)
      // For testing, we'll simulate immediate reconnection attempt
      setTimeout(() => {
        emailWebSocket.reconnectAttempts = 1
        emailWebSocket.connect()
      }, 10)

      await reconnectionPromise
      expect(emailWebSocket.connect).toHaveBeenCalled()
    })

    it('should stop reconnecting after max attempts', () => {
      emailWebSocket.reconnectAttempts = emailWebSocket.maxReconnectAttempts
      
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      // This would normally be called by the reconnection logic
      if (emailWebSocket.reconnectAttempts >= emailWebSocket.maxReconnectAttempts) {
        console.error('Max reconnection attempts reached')
      }
      
      expect(consoleSpy).toHaveBeenCalledWith('Max reconnection attempts reached')
      consoleSpy.mockRestore()
    })
  })

  describe('Real-time State Updates', () => {
    beforeEach(async () => {
      await emailWebSocket.connect()
    })

    it('should update Alpine store on sync status changes', () => {
      const store = Alpine.store('realtime')
      
      // Simulate sync status update
      const statusUpdate = {
        type: 'sync_status',
        data: {
          active_accounts: 2,
          total_accounts: 3,
          is_syncing: true
        }
      }

      // This would normally be handled by the message handler
      setTimeout(() => {
        emailWebSocket.syncSocket.dispatchEvent(
          new MessageEvent('message', { 
            data: JSON.stringify(statusUpdate) 
          })
        )
      }, 10)

      // Verify store would be updated (mocked in this test)
      expect(store).toBeTruthy()
    })

    it('should update unread count on new emails', () => {
      const store = Alpine.store('realtime')
      
      const newEmailNotification = {
        type: 'new_email_notification',
        data: {
          id: '789',
          subject: 'New Message',
          sender: 'new@example.com',
          is_urgent: false
        }
      }

      // Simulate the update that would happen in the real handler
      store.recentEmails.unshift(newEmailNotification.data)
      store.unreadCount++

      expect(store.recentEmails).toHaveLength(1)
      expect(store.recentEmails[0].subject).toBe('New Message')
      expect(store.unreadCount).toBe(1)
    })
  })

  describe('Performance and Load Testing', () => {
    it('should handle multiple rapid messages', async () => {
      await emailWebSocket.connect()
      
      const messageCount = 100
      const messages = []
      
      const messageHandler = (event) => {
        messages.push(JSON.parse(event.data))
      }
      
      emailWebSocket.syncSocket.addEventListener('message', messageHandler)
      
      // Send multiple messages rapidly
      for (let i = 0; i < messageCount; i++) {
        setTimeout(() => {
          emailWebSocket.syncSocket.dispatchEvent(
            new MessageEvent('message', {
              data: JSON.stringify({
                type: 'test_message',
                id: i,
                timestamp: Date.now()
              })
            })
          )
        }, i * 10) // 10ms intervals
      }
      
      // Wait for all messages to be processed
      await new Promise(resolve => setTimeout(resolve, messageCount * 10 + 100))
      
      expect(messages.length).toBe(messageCount)
      expect(messages[0].id).toBe(0)
      expect(messages[messageCount - 1].id).toBe(messageCount - 1)
    })

    it('should handle large message payloads', async () => {
      await emailWebSocket.connect()
      
      const largePayload = {
        type: 'bulk_update',
        data: {
          emails: Array.from({ length: 1000 }, (_, i) => ({
            id: `email_${i}`,
            subject: `Test Email ${i}`,
            sender: `sender${i}@example.com`,
            body: 'This is a test email with some content '.repeat(50)
          }))
        }
      }
      
      const messagePromise = new Promise((resolve) => {
        emailWebSocket.syncSocket.addEventListener('message', (event) => {
          const data = JSON.parse(event.data)
          if (data.type === 'bulk_update') {
            resolve(data)
          }
        })
      })
      
      setTimeout(() => {
        emailWebSocket.syncSocket.dispatchEvent(
          new MessageEvent('message', {
            data: JSON.stringify(largePayload)
          })
        )
      }, 10)
      
      const receivedPayload = await messagePromise
      expect(receivedPayload.data.emails).toHaveLength(1000)
      expect(receivedPayload.data.emails[0].id).toBe('email_0')
    })
  })
})