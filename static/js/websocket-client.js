/**
 * Real-time WebSocket client for email notifications and sync updates
 * Integrates with Alpine.js for reactive UI updates
 */

class EmailWebSocketClient {
    constructor() {
        this.syncSocket = null;
        this.notificationSocket = null;
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        
        // Event handlers
        this.onSyncUpdate = null;
        this.onNotification = null;
        this.onConnectionChange = null;
        
        // Initialize Alpine store for real-time data
        this.initializeAlpineStore();
    }
    
    initializeAlpineStore() {
        if (typeof Alpine === 'undefined') {
            console.warn('Alpine.js not found, WebSocket client will work but without reactive updates');
            return;
        }
        
        Alpine.store('realtime', {
            // Connection status
            syncConnected: false,
            notificationsConnected: false,
            
            // Sync data
            syncStatus: {
                active_accounts: 0,
                total_accounts: 0,
                last_sync: null,
                is_syncing: false
            },
            
            // Notifications
            unreadCount: 0,
            recentNotifications: [],
            
            // Email data
            recentEmails: [],
            
            // Methods
            markEmailRead(emailId) {
                if (this.syncConnected) {
                    window.emailWebSocket.markEmailRead([emailId]);
                }
            },
            
            startSync(forceFullSync = false) {
                if (this.syncConnected) {
                    window.emailWebSocket.startSync(forceFullSync);
                }
            },
            
            addNotification(notification) {
                this.recentNotifications.unshift(notification);
                if (this.recentNotifications.length > 10) {
                    this.recentNotifications = this.recentNotifications.slice(0, 10);
                }
            },
            
            removeNotification(id) {
                this.recentNotifications = this.recentNotifications.filter(n => n.id !== id);
            }
        });
    }
    
    connect() {
        // Only connect for authenticated users to avoid noisy errors before login
        if (!window.fyxeraiUserAuthenticated) {
            console.log('Realtime: user not authenticated; skipping WebSocket connect');
            return;
        }
        if (this.isConnecting) return;
        
        this.isConnecting = true;
        
        try {
            this.connectSyncWebSocket();
            this.connectNotificationWebSocket();
        } catch (error) {
            console.error('Failed to connect WebSockets:', error);
            this.isConnecting = false;
        }
    }
    
    connectSyncWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/email-sync/`;
        
        this.syncSocket = new WebSocket(wsUrl);
        
        this.syncSocket.onopen = () => {
            console.log('Sync WebSocket connected');
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.isConnecting = false;
            
            if (Alpine.store('realtime')) {
                Alpine.store('realtime').syncConnected = true;
            }
            
            this.notifyConnectionChange('sync', true);
            
            // Request initial status
            this.sendSyncMessage({ type: 'get_status' });
        };
        
        this.syncSocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleSyncMessage(data);
            } catch (error) {
                console.error('Error parsing sync message:', error);
            }
        };
        
        this.syncSocket.onclose = () => {
            console.log('Sync WebSocket disconnected');
            if (Alpine.store('realtime')) {
                Alpine.store('realtime').syncConnected = false;
            }
            this.notifyConnectionChange('sync', false);
            this.scheduleReconnect('sync');
        };
        
        this.syncSocket.onerror = (error) => {
            console.error('Sync WebSocket error:', error);
        };
    }
    
    connectNotificationWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        this.notificationSocket = new WebSocket(wsUrl);
        
        this.notificationSocket.onopen = () => {
            console.log('Notification WebSocket connected');
            
            if (Alpine.store('realtime')) {
                Alpine.store('realtime').notificationsConnected = true;
            }
            
            this.notifyConnectionChange('notifications', true);
            
            // Subscribe to notifications
            this.sendNotificationMessage({ type: 'subscribe_notifications' });
            this.sendNotificationMessage({ type: 'get_unread_count' });
        };
        
        this.notificationSocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleNotificationMessage(data);
            } catch (error) {
                console.error('Error parsing notification message:', error);
            }
        };
        
        this.notificationSocket.onclose = () => {
            console.log('Notification WebSocket disconnected');
            if (Alpine.store('realtime')) {
                Alpine.store('realtime').notificationsConnected = false;
            }
            this.notifyConnectionChange('notifications', false);
            this.scheduleReconnect('notifications');
        };
        
        this.notificationSocket.onerror = (error) => {
            console.error('Notification WebSocket error:', error);
        };
    }
    
    handleSyncMessage(data) {
        console.log('Sync message received:', data);
        
        const store = Alpine.store('realtime');
        
        switch (data.type) {
            case 'sync_status':
                if (store) {
                    store.syncStatus = { ...store.syncStatus, ...data.data };
                }
                break;
                
            case 'sync_started':
                if (store) {
                    store.syncStatus.is_syncing = true;
                }
                this.showNotification('Sync started', 'info');
                break;
                
            case 'sync_progress':
                if (store) {
                    store.syncStatus = { ...store.syncStatus, ...data.data };
                }
                break;
                
            case 'sync_completed':
                if (store) {
                    store.syncStatus.is_syncing = false;
                    store.syncStatus = { ...store.syncStatus, ...data.data };
                }
                this.showNotification(`Sync completed: ${data.data.accounts_synced} accounts`, 'success');
                break;
                
            case 'email_categorized':
                this.showNotification(`Email recategorized: ${data.data.new_category}`, 'info');
                break;
                
            case 'emails_marked_read':
                this.showNotification(`${data.count} emails marked as read`, 'success');
                break;
                
            case 'error':
                this.showNotification(data.message, 'error');
                break;
        }
        
        // Custom event handler
        if (this.onSyncUpdate) {
            this.onSyncUpdate(data);
        }
    }
    
    handleNotificationMessage(data) {
        console.log('Notification message received:', data);
        
        const store = Alpine.store('realtime');
        
        switch (data.type) {
            case 'connected':
                this.showNotification('Real-time notifications enabled', 'success');
                break;
                
            case 'new_email_notification':
                if (store) {
                    store.recentEmails.unshift(data.data);
                    if (store.recentEmails.length > 20) {
                        store.recentEmails = store.recentEmails.slice(0, 20);
                    }
                    store.unreadCount++;
                }
                this.showEmailNotification(data.data);
                break;
                
            case 'urgent_alert':
                this.showUrgentAlert(data.data);
                break;
                
            case 'unread_count':
                if (store) {
                    store.unreadCount = data.count;
                }
                break;
                
            case 'account_connected':
                this.showNotification(data.data.message, 'success');
                // Attempt to refresh the Accounts view so the new account appears immediately
                try {
                    const accountsTab = document.querySelector('[data-tab="accounts"]');
                    if (accountsTab) {
                        // Switch visual state and trigger HTMX load if present
                        if (window.htmx) {
                            window.htmx.trigger(accountsTab, 'click');
                        }
                    } else if (window.htmx) {
                        // Fallback: directly load accounts partial into main content
                        window.htmx.ajax('GET', '/partials/email-accounts/', '#main-content');
                    }

                    // Refresh sidebar nested account list if present
                    const sidebarList = document.getElementById('sidebar-account-list');
                    if (sidebarList && window.htmx) {
                        window.htmx.ajax('GET', '/account-menu/', '#sidebar-account-list');
                    }

                    // Update sidebar account count badge if present
                    const sidebarCount = document.getElementById('sidebar-account-count');
                    if (sidebarCount) {
                        const current = parseInt(sidebarCount.textContent || '0', 10);
                        if (!isNaN(current)) sidebarCount.textContent = String(current + 1);
                    }
                } catch (e) {
                    console.warn('Could not refresh Accounts view after account_connected:', e);
                }
                break;
                
            case 'account_error':
                this.showNotification(`Account error: ${data.data.error_message}`, 'error');
                break;
                
            case 'sync_status_update':
                if (store) {
                    store.syncStatus = { ...store.syncStatus, ...data.data };
                }
                break;
                
            case 'error':
                this.showNotification(data.message, 'error');
                break;
        }
        
        // Custom event handler
        if (this.onNotification) {
            this.onNotification(data);
        }
    }
    
    // Public methods for sending messages
    startSync(forceFullSync = false) {
        this.sendSyncMessage({
            type: 'start_sync',
            force_full_sync: forceFullSync
        });
    }
    
    markEmailRead(emailIds) {
        this.sendSyncMessage({
            type: 'mark_read',
            email_ids: emailIds
        });
    }
    
    getSyncStatus() {
        this.sendSyncMessage({ type: 'get_status' });
    }
    
    getUnreadCount() {
        this.sendNotificationMessage({ type: 'get_unread_count' });
    }
    
    updateNotificationPreferences(preferences) {
        this.sendNotificationMessage({
            type: 'update_preferences',
            preferences: preferences
        });
    }
    
    // Helper methods
    sendSyncMessage(message) {
        if (this.syncSocket && this.syncSocket.readyState === WebSocket.OPEN) {
            this.syncSocket.send(JSON.stringify(message));
        } else {
            console.warn('Sync WebSocket not connected');
        }
    }
    
    sendNotificationMessage(message) {
        if (this.notificationSocket && this.notificationSocket.readyState === WebSocket.OPEN) {
            this.notificationSocket.send(JSON.stringify(message));
        } else {
            console.warn('Notification WebSocket not connected');
        }
    }
    
    showNotification(message, type = 'info') {
        // Create a notification object
        const notification = {
            id: Date.now(),
            message: message,
            type: type,
            timestamp: new Date().toISOString()
        };
        
        // Add to Alpine store
        const store = Alpine.store('realtime');
        if (store) {
            store.addNotification(notification);
        }
        
        // Show browser notification if permitted
        this.showBrowserNotification(message, type);
        
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
    
    showEmailNotification(emailData) {
        const message = `New email from ${emailData.sender}: ${emailData.subject}`;
        this.showNotification(message, emailData.is_urgent ? 'urgent' : 'info');
        
        // Play sound for urgent emails
        if (emailData.is_urgent) {
            this.playNotificationSound();
        }
    }
    
    showUrgentAlert(alertData) {
        this.showNotification(alertData.message, 'urgent');
        this.playNotificationSound();
        
        // Show prominent alert in UI
        if (typeof Alpine !== 'undefined') {
            // Trigger urgent alert component
            window.dispatchEvent(new CustomEvent('urgentEmail', { detail: alertData }));
        }
    }
    
    showBrowserNotification(message, type) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const options = {
                icon: '/static/images/fyxerai-icon.png',
                badge: '/static/images/fyxerai-badge.png',
                tag: 'fyxerai-email'
            };
            
            if (type === 'urgent') {
                options.requireInteraction = true;
            }
            
            new Notification('FYXERAI Email Assistant', {
                body: message,
                ...options
            });
        }
    }
    
    playNotificationSound() {
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.3;
            audio.play().catch(e => console.log('Could not play notification sound:', e));
        } catch (e) {
            console.log('Notification sound not available:', e);
        }
    }
    
    scheduleReconnect(socketType) {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
            
            console.log(`Reconnecting ${socketType} WebSocket in ${delay}ms (attempt ${this.reconnectAttempts})`);
            
            setTimeout(() => {
                if (socketType === 'sync') {
                    this.connectSyncWebSocket();
                } else if (socketType === 'notifications') {
                    this.connectNotificationWebSocket();
                }
            }, delay);
        } else {
            console.error(`Max reconnection attempts reached for ${socketType} WebSocket`);
        }
    }
    
    notifyConnectionChange(socketType, connected) {
        if (this.onConnectionChange) {
            this.onConnectionChange(socketType, connected);
        }
        
        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('websocketConnectionChange', {
            detail: { socketType, connected }
        }));
    }
    
    disconnect() {
        if (this.syncSocket) {
            this.syncSocket.close();
            this.syncSocket = null;
        }
        
        if (this.notificationSocket) {
            this.notificationSocket.close();
            this.notificationSocket = null;
        }
        
        console.log('WebSocket connections closed');
    }
    
    // Request notification permission
    static async requestNotificationPermission() {
        try {
            if (!('Notification' in window)) return false;
            // Avoid prompting automatically on browsers that require a user gesture
            if (Notification.permission !== 'default') return Notification.permission === 'granted';
            // Defer requesting permission until user gesture elsewhere in the app
            // Here we simply no-op to prevent console errors in Safari/WebKit
            return false;
        } catch (e) {
            // Swallow errors from strict browsers (Safari: user gesture required)
            return false;
        }
    }
}

// Initialize global WebSocket client
window.emailWebSocket = new EmailWebSocketClient();

// Auto-connect when DOM is ready (only for authenticated users)
document.addEventListener('DOMContentLoaded', () => {
    // Only connect WebSockets if user is authenticated
    if (window.fyxeraiUserAuthenticated) {
        // Request notification permission
        EmailWebSocketClient.requestNotificationPermission();
        
        // Connect WebSockets
        window.emailWebSocket.connect();
    } else {
        console.log('WebSocket connections disabled - user not authenticated');
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.emailWebSocket) {
        window.emailWebSocket.disconnect();
    }
});
