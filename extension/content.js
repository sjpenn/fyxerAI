/**
 * FYXERAI Chrome Extension - Content Script
 * Injects FYXERAI functionality into Gmail and Outlook web interfaces
 * CSP-compliant version with TrustedScript support
 */

console.log('FYXERAI Content Script: Loading... (Version 1.3 - CSP Compliant)');



// Helper function to create element with safe text content
function createElementWithText(tagName, className = '', textContent = '') {
    const element = document.createElement(tagName);
    if (className) element.className = className;
    if (textContent) element.textContent = textContent;
    return element;
}

// Helper function to check if we can use Trusted Types
function canUseTrustedTypes() {
    return window.trustedTypes && window.trustedTypes.createPolicy;
}

// Detect email platform
const isGmail = window.location.hostname === 'mail.google.com';
const isOutlook = window.location.hostname.includes('outlook');

console.log(`FYXERAI Content Script: Detected platform - Gmail: ${isGmail}, Outlook: ${isOutlook}`);

// FYXERAI UI Controller
class FyxerAIController {
    constructor() {
        this.initialized = false;
        this.emailData = {};
        this.apiEndpoint = 'http://localhost:8000';
    }

    async init() {
        if (this.initialized) return;
        
        console.log('FYXERAI: Initializing email assistant...');
        
        try {
            // Wait for email interface to load
            await this.waitForEmailInterface();
            
            // Inject FYXERAI UI elements
            this.injectUI();
            
            // Set up email monitoring
            this.setupEmailMonitoring();
            
            this.initialized = true;
            console.log('FYXERAI: Successfully initialized');
            
        } catch (error) {
            console.error('FYXERAI: Initialization failed:', error);
        }
    }

    async waitForEmailInterface() {
        const maxWait = 10000; // 10 seconds
        const checkInterval = 500; // 500ms
        let waited = 0;

        return new Promise((resolve, reject) => {
            const checkForInterface = () => {
                let interfaceReady = false;

                if (isGmail) {
                    // Check for Gmail interface elements
                    interfaceReady = document.querySelector('[role="main"]') !== null ||
                                   document.querySelector('.nH') !== null;
                } else if (isOutlook) {
                    // Check for Outlook interface elements
                    interfaceReady = document.querySelector('[role="main"]') !== null ||
                                   document.querySelector('.ms-FocusZone') !== null;
                }

                if (interfaceReady) {
                    resolve();
                } else if (waited >= maxWait) {
                    reject(new Error('Email interface did not load in time'));
                } else {
                    waited += checkInterval;
                    setTimeout(checkForInterface, checkInterval);
                }
            };

            checkForInterface();
        });
    }

    injectUI() {
        console.log('FYXERAI: Injecting UI elements...');

        // Create FYXERAI control panel
        this.createControlPanel();

        // Add category buttons to emails
        this.addCategoryButtons();

        // Add AI draft button
        this.addAIDraftButton();
    }

    createControlPanel() {
        try {
            // Remove existing panel if present
            const existingPanel = document.getElementById('fyxerai-panel');
            if (existingPanel) {
                existingPanel.remove();
            }

            // Create floating control panel
            const panel = document.createElement('div');
            panel.id = 'fyxerai-panel';
            panel.className = 'fyxerai-control-panel';
            
            // Build panel content safely
            const headerDiv = document.createElement('div');
            headerDiv.className = 'fyxerai-panel-header';
            
            const logo = document.createElement('div');
            logo.className = 'fyxerai-logo';
            logo.textContent = 'F';
            
            const title = document.createElement('span');
            title.className = 'fyxerai-title';
            title.textContent = 'FYXERAI';
            
            const closeBtn = document.createElement('button');
            closeBtn.className = 'fyxerai-close';
            closeBtn.id = 'fyxerai-close-panel';
            closeBtn.textContent = '×';
            
            headerDiv.appendChild(logo);
            headerDiv.appendChild(title);
            headerDiv.appendChild(closeBtn);
            
            // Content section
            const contentDiv = document.createElement('div');
            contentDiv.className = 'fyxerai-panel-content';
            
            // Status section
            const statusDiv = document.createElement('div');
            statusDiv.className = 'fyxerai-status';
            
            const statusIndicator = document.createElement('div');
            statusIndicator.className = 'fyxerai-connection-status';
            statusIndicator.id = 'fyxerai-status';
            
            const statusDot = document.createElement('div');
            statusDot.className = 'fyxerai-status-dot';
            
            const statusText = document.createElement('span');
            statusText.textContent = 'Connecting...';
            
            statusIndicator.appendChild(statusDot);
            statusIndicator.appendChild(statusText);
            statusDiv.appendChild(statusIndicator);
            
            // Actions section
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'fyxerai-actions';
            
            const triageBtn = document.createElement('button');
            triageBtn.className = 'fyxerai-btn fyxerai-btn-primary';
            triageBtn.id = 'fyxerai-triage-inbox';
            triageBtn.textContent = 'Triage Inbox';
            
            const draftsBtn = document.createElement('button');
            draftsBtn.className = 'fyxerai-btn fyxerai-btn-secondary';
            draftsBtn.id = 'fyxerai-generate-drafts';
            draftsBtn.textContent = 'Generate Drafts';
            
            actionsDiv.appendChild(triageBtn);
            actionsDiv.appendChild(draftsBtn);
            
            // Stats section
            const statsDiv = document.createElement('div');
            statsDiv.className = 'fyxerai-stats';
            
            const stat1 = document.createElement('div');
            stat1.className = 'fyxerai-stat';
            const stat1Number = document.createElement('span');
            stat1Number.className = 'fyxerai-stat-number';
            stat1Number.id = 'fyxerai-emails-processed';
            stat1Number.textContent = '0';
            const stat1Label = document.createElement('span');
            stat1Label.className = 'fyxerai-stat-label';
            stat1Label.textContent = 'Emails Triaged';
            stat1.appendChild(stat1Number);
            stat1.appendChild(stat1Label);
            
            const stat2 = document.createElement('div');
            stat2.className = 'fyxerai-stat';
            const stat2Number = document.createElement('span');
            stat2Number.className = 'fyxerai-stat-number';
            stat2Number.id = 'fyxerai-drafts-created';
            stat2Number.textContent = '0';
            const stat2Label = document.createElement('span');
            stat2Label.className = 'fyxerai-stat-label';
            stat2Label.textContent = 'Drafts Created';
            stat2.appendChild(stat2Number);
            stat2.appendChild(stat2Label);
            
            statsDiv.appendChild(stat1);
            statsDiv.appendChild(stat2);
            
            // Assemble content
            contentDiv.appendChild(statusDiv);
            contentDiv.appendChild(actionsDiv);
            contentDiv.appendChild(statsDiv);
            
            // Assemble panel
            panel.appendChild(headerDiv);
            panel.appendChild(contentDiv);

            // Safely append to body
            if (document.body) {
                document.body.appendChild(panel);
                
                // Add event listeners
                this.setupPanelEventListeners();
                
                // Test connection
                this.testConnection();
                
                console.log('FYXERAI: Control panel created successfully');
            } else {
                console.error('FYXERAI: Cannot inject panel - document.body not available');
            }
        } catch (error) {
            console.error('FYXERAI: Failed to create control panel:', error);
        }
    }

    setupPanelEventListeners() {
        // Close panel
        document.getElementById('fyxerai-close-panel').addEventListener('click', () => {
            document.getElementById('fyxerai-panel').style.display = 'none';
        });

        // Triage inbox
        document.getElementById('fyxerai-triage-inbox').addEventListener('click', () => {
            this.triageInbox();
        });

        // Generate drafts
        document.getElementById('fyxerai-generate-drafts').addEventListener('click', () => {
            this.generateDrafts();
        });
    }

    addCategoryButtons() {
        if (isGmail) {
            this.addGmailCategoryButtons();
        } else if (isOutlook) {
            this.addOutlookCategoryButtons();
        }
    }

    addGmailCategoryButtons() {
        // Find Gmail email elements and add category buttons
        const emailElements = document.querySelectorAll('[data-thread-id], [data-fyxerai-id]');
        
        let addedCount = 0;
        
        emailElements.forEach((emailElement, index) => {
            // Check if already processed
            if (!emailElement.hasAttribute('data-fyxerai-processed') && 
                !emailElement.querySelector('.fyxerai-category-badge')) {
                
                const badge = this.createCategoryBadge('pending');
                
                // Try to find a good place to insert the badge
                const subjectArea = emailElement.querySelector('.bog, .y6, .bqe');
                if (subjectArea && !subjectArea.querySelector('.fyxerai-category-badge')) {
                    subjectArea.appendChild(badge);
                    addedCount++;
                } else if (!emailElement.querySelector('.fyxerai-category-badge')) {
                    // Fallback: add to the main element
                    emailElement.appendChild(badge);
                    addedCount++;
                }
                
                // Mark as processed
                emailElement.setAttribute('data-fyxerai-processed', 'true');
            }
        });
        
        if (addedCount > 0) {
            console.log(`FYXERAI Content: Added category buttons to ${addedCount} new Gmail emails`);
        }
    }

    addOutlookCategoryButtons() {
        // Find Outlook email elements and add category buttons
        const emailElements = document.querySelectorAll('[role="listitem"]');
        
        emailElements.forEach(emailElement => {
            if (!emailElement.querySelector('.fyxerai-category-badge')) {
                const badge = this.createCategoryBadge('pending');
                emailElement.appendChild(badge);
            }
        });
    }

    createCategoryBadge(category = 'pending') {
        const badge = document.createElement('div');
        badge.className = `fyxerai-category-badge fyxerai-category-${category}`;
        
        // Create elements safely without innerHTML
        const badgeText = document.createElement('span');
        badgeText.className = 'fyxerai-badge-text';
        badgeText.textContent = category.toUpperCase();
        
        const dropdown = document.createElement('div');
        dropdown.className = 'fyxerai-category-dropdown';
        
        // Create category options
        const categories = ['urgent', 'important', 'routine', 'spam'];
        categories.forEach(cat => {
            const option = document.createElement('button');
            option.className = 'fyxerai-category-option';
            option.setAttribute('data-category', cat);
            option.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
            dropdown.appendChild(option);
        });
        
        badge.appendChild(badgeText);
        badge.appendChild(dropdown);

        // Add click handler
        badge.addEventListener('click', (e) => {
            e.stopPropagation();
            const dropdown = badge.querySelector('.fyxerai-category-dropdown');
            dropdown.classList.toggle('show');
        });

        // Add category selection handlers
        badge.querySelectorAll('.fyxerai-category-option').forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const newCategory = e.target.dataset.category;
                this.updateEmailCategory(badge, newCategory);
                dropdown.classList.remove('show');
            });
        });

        return badge;
    }

    addAIDraftButton() {
        // Add AI draft button when composing/replying
        const composeElements = document.querySelectorAll('[role="dialog"], .T-I-J3');
        
        composeElements.forEach(element => {
            if (!element.querySelector('.fyxerai-draft-btn')) {
                const draftBtn = document.createElement('button');
                draftBtn.className = 'fyxerai-draft-btn fyxerai-btn fyxerai-btn-ai';
                draftBtn.textContent = '✨ Generate AI Draft';
                draftBtn.addEventListener('click', () => this.generateAIDraft());
                
                element.appendChild(draftBtn);
            }
        });
    }

    setupEmailMonitoring() {
        // Add debouncing to prevent excessive calls
        let debounceTimer = null;
        let isProcessing = false;
        
        const debouncedUpdate = () => {
            if (isProcessing) return;
            
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                if (!isProcessing) {
                    isProcessing = true;
                    try {
                        this.addCategoryButtons();
                        this.addAIDraftButton();
                    } catch (error) {
                        console.warn('FYXERAI: Error updating UI elements:', error);
                    } finally {
                        isProcessing = false;
                    }
                }
            }, 500); // 500ms debounce
        };
        
        // Monitor for new emails and UI changes with improved targeting
        const observer = new MutationObserver((mutations) => {
            let shouldUpdate = false;
            
            mutations.forEach((mutation) => {
                if (mutation.addedNodes.length > 0) {
                    // Only update if we detect email-related changes
                    for (let node of mutation.addedNodes) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            // Check for Gmail email containers or Outlook email elements
                            if (node.querySelector && (
                                node.querySelector('[data-thread-id]') ||
                                node.querySelector('[role="listitem"]') ||
                                node.classList.contains('zA') ||
                                node.classList.contains('yW')
                            )) {
                                shouldUpdate = true;
                                break;
                            }
                        }
                    }
                }
            });
            
            if (shouldUpdate) {
                debouncedUpdate();
            }
        });
        
        // Observe more specific containers to reduce noise
        const emailContainer = document.querySelector('[role="main"]') || document.body;
        observer.observe(emailContainer, {
            childList: true,
            subtree: true
        });

        // Set up message listener for background script
        this.setupMessageListener();
    }

    setupMessageListener() {
        // Listen for messages from background script
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            console.log('FYXERAI Content: Received message:', request);

            switch (request.action) {
                case 'initialize':
                    this.handleInitialize(request, sendResponse);
                    break;

                case 'extractEmails':
                    this.handleExtractEmails(request, sendResponse);
                    break;

                case 'updateCategories':
                    this.handleUpdateCategories(request, sendResponse);
                    break;

                case 'connectionStatusChanged':
                    this.handleConnectionStatusChanged(request, sendResponse);
                    break;

                case 'categorizeSelection':
                    this.handleCategorizeSelection(request, sendResponse);
                    break;

                case 'generateReplyForSelection':
                    this.handleGenerateReplyForSelection(request, sendResponse);
                    break;

                case 'ping':
                    this.handlePing(request, sendResponse);
                    break;

                case 'triageInbox':
                    this.handleTriageInbox(request, sendResponse);
                    break;

                case 'generateDrafts':
                    this.handleGenerateDrafts(request, sendResponse);
                    break;

                case 'generateAIDraft':
                    this.handleGenerateAIDraft(request, sendResponse);
                    break;

                default:
                    console.warn('FYXERAI Content: Unknown action:', request.action);
                    sendResponse({ success: false, error: 'Unknown action' });
            }

            return true; // Keep message channel open for async responses
        });
    }

    handleInitialize(request, sendResponse) {
        console.log('FYXERAI Content: Reinitializing for platform:', request.platform);
        this.apiEndpoint = request.apiBase || this.apiEndpoint;
        this.init();
        sendResponse({ success: true });
    }

    handleExtractEmails(request, sendResponse) {
        console.log('FYXERAI Content: Extracting emails for:', request.platform);
        
        try {
            const dateLimitDays = request.date_limit_days || 7;
            const emails = this.extractEmailsFromPage(dateLimitDays);
            sendResponse({ 
                success: true, 
                emails: emails,
                date_limit_days: dateLimitDays,
                extracted_count: emails.length
            });
        } catch (error) {
            console.error('FYXERAI Content: Email extraction failed:', error);
            sendResponse({ 
                success: false, 
                error: error.message 
            });
        }
    }

    handleUpdateCategories(request, sendResponse) {
        console.log('FYXERAI Content: Updating categories:', request.categories);
        
        try {
            if (request.categories && Array.isArray(request.categories)) {
                console.log(`FYXERAI Content: Processing ${request.categories.length} category updates`);
                
                request.categories.forEach((categoryResult, index) => {
                    console.log(`FYXERAI Content: Updating email ${categoryResult.email_id} to ${categoryResult.category}`);
                    
                    // Find email by ID and update its badge
                    this.updateEmailCategoryById(categoryResult.email_id, categoryResult.category);
                    
                    // Also store the category in the email element for future reference
                    const emailElement = this.findEmailElementById(categoryResult.email_id);
                    if (emailElement) {
                        emailElement.setAttribute('data-fyxerai-category', categoryResult.category);
                        emailElement.setAttribute('data-fyxerai-confidence', categoryResult.confidence || 0);
                        console.log(`FYXERAI Content: Successfully updated email ${categoryResult.email_id}`);
                    } else {
                        console.warn(`FYXERAI Content: Could not find email element for ${categoryResult.email_id}`);
                    }
                });
                
                // Force refresh of category buttons to ensure they're visible
                setTimeout(() => {
                    this.addCategoryButtons();
                }, 1000);
            }
            sendResponse({ success: true });
        } catch (error) {
            console.error('FYXERAI Content: Category update failed:', error);
            sendResponse({ success: false, error: error.message });
        }
    }

    handleConnectionStatusChanged(request, sendResponse) {
        console.log('FYXERAI Content: Connection status changed:', request.connected);
        
        const statusElement = document.getElementById('fyxerai-status');
        if (statusElement) {
            // Clear existing content
            while (statusElement.firstChild) {
                statusElement.removeChild(statusElement.firstChild);
            }
            
            // Create status dot
            const statusDot = document.createElement('div');
            statusDot.className = request.connected ? 
                'fyxerai-status-dot fyxerai-status-connected' : 
                'fyxerai-status-dot fyxerai-status-disconnected';
            
            // Create status text
            const statusText = document.createElement('span');
            statusText.textContent = request.connected ? 'Connected' : 'Disconnected';
            
            statusElement.appendChild(statusDot);
            statusElement.appendChild(statusText);
        }
        
        sendResponse({ success: true });
    }

    handleCategorizeSelection(request, sendResponse) {
        console.log('FYXERAI Content: Categorizing selection:', request.selectedText);
        // Implementation for right-click categorization
        sendResponse({ success: true });
    }

    handleGenerateReplyForSelection(request, sendResponse) {
        console.log('FYXERAI Content: Generating reply for selection:', request.selectedText);
        // Implementation for right-click reply generation
        sendResponse({ success: true });
    }

    handlePing(request, sendResponse) {
        console.log('FYXERAI Content: Responding to ping');
        sendResponse({ success: true, status: 'alive' });
    }

    handleTriageInbox(request, sendResponse) {
        console.log('FYXERAI Content: Handling triage inbox request');
        this.triageInbox().then((result) => {
            sendResponse({ success: true, result });
        }).catch((error) => {
            sendResponse({ success: false, error: error.message });
        });
    }

    handleGenerateDrafts(request, sendResponse) {
        console.log('FYXERAI Content: Handling generate drafts request');
        this.generateDrafts().then((result) => {
            sendResponse({ success: true, result });
        }).catch((error) => {
            sendResponse({ success: false, error: error.message });
        });
    }

    handleGenerateAIDraft(request, sendResponse) {
        console.log('FYXERAI Content: Handling generate AI draft request');
        this.generateAIDraft().then((result) => {
            sendResponse({ success: true, result });
        }).catch((error) => {
            sendResponse({ success: false, error: error.message });
        });
    }

    extractEmailsFromPage(dateLimitDays = 7) {
        const emails = [];
        
        if (isGmail) {
            return this.extractGmailEmails(dateLimitDays);
        } else if (isOutlook) {
            return this.extractOutlookEmails(dateLimitDays);
        }
        
        return emails;
    }

    extractGmailEmails(dateLimitDays = 7) {
        const emails = [];
        const processedThreadIds = new Set();

        // Broaden selectors and avoid filtering by our UI marker attribute
        let emailElements = document.querySelectorAll('tr[data-thread-id], tr[data-legacy-thread-id], tr.zA');
        if (!emailElements || emailElements.length === 0) {
            // Fallback: search within the main region
            const main = document.querySelector('[role="main"]') || document;
            emailElements = main.querySelectorAll('tr[data-thread-id], tr[data-legacy-thread-id], tr.zA');
        }

        // Calculate cutoff date
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - dateLimitDays);

        console.log(`FYXERAI Content: Found ${emailElements.length} Gmail rows, filtering last ${dateLimitDays} days`);

        emailElements.forEach((element, index) => {
            try {
                const threadId = element.getAttribute('data-thread-id')
                    || element.getAttribute('data-legacy-thread-id')
                    || element.getAttribute('data-fyxerai-id')
                    || `gmail-${Date.now()}-${index}`;

                // Deduplicate by thread ID in this run
                if (processedThreadIds.has(threadId)) return;
                processedThreadIds.add(threadId);

                const subjectElement = element.querySelector('[data-thread-subject], .bog, .y6 span[id], .bqe span, .bog span');
                const senderElement = element.querySelector('[email], .yW span, .yX span, .bA4 span, .go span');
                const timeElement = element.querySelector('time[datetime], [title*="GMT"], .xY span, .xW span');

                // Extract and parse email date
                const emailDate = this._parseEmailDate(timeElement);

                // Skip emails older than cutoff date
                if (emailDate && emailDate < cutoffDate) {
                    // console.debug(`FYXERAI Content: Skipping old email from ${emailDate.toLocaleDateString()}`);
                    return;
                }

                // Add our own ID attribute for tracking (do NOT set data-fyxerai-processed here)
                if (!element.getAttribute('data-fyxerai-id')) {
                    element.setAttribute('data-fyxerai-id', threadId);
                }

                const email = {
                    id: threadId,
                    platform: 'gmail',
                    subject: subjectElement?.textContent?.trim() || 'No Subject',
                    sender: senderElement?.textContent?.trim() || 'Unknown Sender',
                    time: timeElement?.getAttribute('title') || timeElement?.getAttribute?.('datetime') || timeElement?.textContent || '',
                    date: emailDate,
                    category: 'pending',
                    element: element
                };

                // console.log(`FYXERAI Content: Extracted email ${threadId}: "${email.subject}" from ${email.sender}`);
                emails.push(email);
            } catch (error) {
                console.warn('FYXERAI Content: Failed to extract Gmail email:', error);
            }
        });

        console.log(`FYXERAI Content: Extracted ${emails.length} Gmail emails (${dateLimitDays}-day window)`);
        return emails;
    }

    extractOutlookEmails() {
        const emails = [];
        const emailElements = document.querySelectorAll('[role="listitem"], .ms-List-cell');
        
        emailElements.forEach((element, index) => {
            try {
                const messageId = element.getAttribute('data-convid') || `outlook-${index}`;
                const subjectElement = element.querySelector('[data-automation-id="subjectLine"]');
                const senderElement = element.querySelector('[data-automation-id="senderDisplayName"]');
                const timeElement = element.querySelector('[data-automation-id="receivedTime"]');
                
                const email = {
                    id: messageId,
                    platform: 'outlook',
                    subject: subjectElement?.textContent?.trim() || 'No Subject',
                    sender: senderElement?.textContent?.trim() || 'Unknown Sender',
                    time: timeElement?.textContent || '',
                    category: 'pending',
                    element: element
                };
                
                emails.push(email);
            } catch (error) {
                console.warn('FYXERAI Content: Failed to extract Outlook email:', error);
            }
        });
        
        return emails;
    }

    findEmailElementById(emailId) {
        // Try different selectors for Gmail and Outlook
        let emailElement = document.querySelector(`[data-thread-id="${emailId}"]`)
            || document.querySelector(`[data-legacy-thread-id="${emailId}"]`)
            || document.querySelector(`[data-fyxerai-id="${emailId}"]`);
        if (!emailElement) {
            const allEmails = document.querySelectorAll('[data-thread-id], [data-legacy-thread-id], [role="listitem"]');
            for (let email of allEmails) {
                if (email.getAttribute('data-fyxerai-id') === emailId
                    || email.getAttribute('data-legacy-thread-id') === emailId
                    || email.getAttribute('data-thread-id') === emailId) {
                    emailElement = email;
                    break;
                }
            }
        }
        return emailElement;
    }

    updateEmailCategoryById(emailId, category) {
        // Find the email element by ID and update its category
        const emailElement = this.findEmailElementById(emailId);
        if (emailElement) {
            let badge = emailElement.querySelector('.fyxerai-category-badge');
            if (!badge) {
                // Create badge if it doesn't exist
                badge = this.createCategoryBadge(category);
                emailElement.appendChild(badge);
            } else {
                // Update existing badge
                this.updateEmailCategory(badge, category);
            }
        } else {
            console.warn(`FYXERAI Content: Could not find email element for ID: ${emailId}`);
        }
    }

    async testConnection() {
        const statusElement = document.getElementById('fyxerai-status');
        
        try {
            console.log('FYXERAI: Testing connection via background script...');
            
            // Show loading state
            this.updateConnectionStatus('connecting', 'Connecting...');
            
            // Use background script for all API calls to avoid CSP issues
            const response = await chrome.runtime.sendMessage({
                action: 'checkConnection',
                platform: isGmail ? 'gmail' : 'outlook'
            });

            if (response && response.success && response.connected) {
                this.updateConnectionStatus('connected', 'Connected');
                console.log('FYXERAI: Successfully connected to backend via background script');
                
                // Show success message briefly
                this.showNotification('Connected to FYXERAI backend', 'success');
            } else {
                throw new Error(response?.error || 'Backend not responding');
            }
        } catch (error) {
            this.updateConnectionStatus('disconnected', 'Disconnected');
            console.warn('FYXERAI: Backend connection failed:', error);
            
            // Show error notification
            this.showNotification(`Connection failed: ${error.message}`, 'error');
        }
    }

    updateConnectionStatus(status, text) {
        const statusElement = document.getElementById('fyxerai-status');
        if (!statusElement) return;
        
        // Clear existing content
        while (statusElement.firstChild) {
            statusElement.removeChild(statusElement.firstChild);
        }
        
        // Create status dot
        const statusDot = document.createElement('div');
        statusDot.className = `fyxerai-status-dot fyxerai-status-${status}`;
        
        // Create status text
        const statusText = document.createElement('span');
        statusText.textContent = text;
        
        statusElement.appendChild(statusDot);
        statusElement.appendChild(statusText);
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fyxerai-notification fyxerai-notification-${type}`;
        notification.textContent = message;
        
        // Add to panel if it exists
        const panel = document.getElementById('fyxerai-panel');
        if (panel) {
            panel.appendChild(notification);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 5000);
        }
        
        console.log(`FYXERAI Notification (${type}): ${message}`);
    }

    async triageInbox() {
        console.log('FYXERAI: Starting inbox triage...');
        
        try {
            // Show loading state
            this.showNotification('Starting email triage...', 'info');
            this.disableTriageButton(true);
            
            // Send message to background script
            const response = await chrome.runtime.sendMessage({
                action: 'triageInbox',
                platform: isGmail ? 'gmail' : 'outlook'
            });

            if (response && response.success) {
                this.updateStats('emails', response.processed || 0);
                this.showNotification(response.message || `Triaged ${response.processed} emails successfully`, 'success');
                console.log('FYXERAI: Inbox triage completed');
            } else {
                throw new Error(response?.error || 'Triage failed');
            }
        } catch (error) {
            console.error('FYXERAI: Triage failed:', error);
            this.showNotification(`Triage failed: ${error.message}`, 'error');
        } finally {
            this.disableTriageButton(false);
        }
    }

    disableTriageButton(disabled) {
        const triageBtn = document.getElementById('fyxerai-triage-inbox');
        if (triageBtn) {
            triageBtn.disabled = disabled;
            triageBtn.textContent = disabled ? 'Triaging...' : 'Triage Inbox';
        }
    }

    async generateDrafts() {
        console.log('FYXERAI: Generating AI drafts...');
        
        try {
            // Show loading state
            this.showNotification('Generating AI drafts...', 'info');
            this.disableDraftsButton(true);
            
            const response = await chrome.runtime.sendMessage({
                action: 'generateDrafts',
                platform: isGmail ? 'gmail' : 'outlook'
            });

            if (response && response.success) {
                this.updateStats('drafts', response.created || 0);
                this.showNotification(response.message || `Generated ${response.created} drafts successfully`, 'success');
                console.log('FYXERAI: Draft generation completed');
            } else {
                throw new Error(response?.error || 'Draft generation failed');
            }
        } catch (error) {
            console.error('FYXERAI: Draft generation failed:', error);
            this.showNotification(`Draft generation failed: ${error.message}`, 'error');
        } finally {
            this.disableDraftsButton(false);
        }
    }

    disableDraftsButton(disabled) {
        const draftsBtn = document.getElementById('fyxerai-generate-drafts');
        if (draftsBtn) {
            draftsBtn.disabled = disabled;
            draftsBtn.textContent = disabled ? 'Generating...' : 'Generate Drafts';
        }
    }

    async generateAIDraft() {
        console.log('FYXERAI: Generating AI draft for current email...');
        
        try {
            const emailContent = this.extractEmailContent();
            
            if (!emailContent.subject && !emailContent.body) {
                throw new Error('No email content found to generate draft from');
            }
            
            this.showNotification('Generating AI draft...', 'info');
            
            const response = await chrome.runtime.sendMessage({
                action: 'generateAIDraft',
                emailContent: emailContent,
                platform: isGmail ? 'gmail' : 'outlook'
            });

            if (response && response.success && response.draft) {
                this.insertDraftContent(response.draft);
                this.showNotification(response.message || 'AI draft generated successfully', 'success');
                console.log('FYXERAI: AI draft generated successfully');
            } else {
                throw new Error(response?.error || 'Failed to generate AI draft');
            }
        } catch (error) {
            console.error('FYXERAI: AI draft generation failed:', error);
            this.showNotification(`AI draft failed: ${error.message}`, 'error');
        }
    }

    extractEmailContent() {
        // Extract email content based on platform
        if (isGmail) {
            const subject = document.querySelector('[name="subject"]')?.value || '';
            const body = document.querySelector('[role="textbox"]')?.textContent || '';
            return { subject, body };
        } else if (isOutlook) {
            const subject = document.querySelector('[aria-label*="Subject"]')?.value || '';
            const body = document.querySelector('[role="textbox"]')?.textContent || '';
            return { subject, body };
        }
        return {};
    }

    insertDraftContent(draft) {
        // Insert AI-generated draft into compose window safely
        const composeBox = document.querySelector('[role="textbox"]');
        if (composeBox) {
            // Use textContent instead of innerHTML for security
            composeBox.textContent = draft;
            
            // Trigger input event to notify the email client
            const inputEvent = new Event('input', { bubbles: true, cancelable: true });
            composeBox.dispatchEvent(inputEvent);
            
            // Also trigger change event for compatibility
            const changeEvent = new Event('change', { bubbles: true, cancelable: true });
            composeBox.dispatchEvent(changeEvent);
        }
    }

    updateEmailCategory(badge, category) {
        badge.className = `fyxerai-category-badge fyxerai-category-${category}`;
        badge.querySelector('.fyxerai-badge-text').textContent = category.toUpperCase();
        
        // Hide dropdown
        badge.querySelector('.fyxerai-category-dropdown').classList.remove('show');
        
        console.log(`FYXERAI: Email categorized as ${category}`);
    }

    updateStats(type, value) {
        const statElement = document.getElementById(`fyxerai-${type}-processed`) || 
                           document.getElementById(`fyxerai-${type}-created`);
        if (statElement) {
            statElement.textContent = value;
        }
    }
    
    _parseEmailDate(timeElement) {
        // Helper function to parse email date from Gmail time elements
        if (!timeElement) return new Date();
        
        try {
            // Try to get the full date from title attribute (GMT format)
            const titleDate = timeElement.getAttribute('title');
            if (titleDate) {
                return new Date(titleDate);
            }
            
            // Fallback: parse text content (relative dates like "2 hours ago")
            const timeText = timeElement.textContent.trim();
            if (timeText) {
                return this._parseRelativeDate(timeText);
            }
            
        } catch (error) {
            console.warn('FYXERAI Content: Failed to parse email date:', error);
        }
        
        return new Date(); // Default to current date
    }
    
    _parseRelativeDate(timeText) {
        // Parse relative dates like "2 hours ago", "yesterday", "3 days ago"
        const now = new Date();
        
        if (timeText.includes('hour') || timeText.includes('minute') || timeText.includes('second')) {
            return now; // Same day
        }
        
        if (timeText.includes('yesterday')) {
            const yesterday = new Date(now);
            yesterday.setDate(now.getDate() - 1);
            return yesterday;
        }
        
        const dayMatch = timeText.match(/(\d+)\s*day/);
        if (dayMatch) {
            const daysAgo = parseInt(dayMatch[1]);
            const date = new Date(now);
            date.setDate(now.getDate() - daysAgo);
            return date;
        }
        
        const weekMatch = timeText.match(/(\d+)\s*week/);
        if (weekMatch) {
            const weeksAgo = parseInt(weekMatch[1]);
            const date = new Date(now);
            date.setDate(now.getDate() - (weeksAgo * 7));
            return date;
        }
        
        // If we can't parse it, assume it's recent
        return now;
    }
}

// Initialize FYXERAI when DOM is ready
let fyxerAI;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        fyxerAI = new FyxerAIController();
        fyxerAI.init();
    });
} else {
    fyxerAI = new FyxerAIController();
    fyxerAI.init();
}

// Handle page navigation in single-page applications
let currentUrl = window.location.href;
setInterval(() => {
    if (window.location.href !== currentUrl) {
        currentUrl = window.location.href;
        if (fyxerAI) {
            setTimeout(() => fyxerAI.init(), 1000); // Re-initialize after navigation
        }
    }
}, 1000);

console.log('FYXERAI Content Script: Loaded successfully');
