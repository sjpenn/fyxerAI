/**
 * FYXERAI Chrome Extension - Background Script (Service Worker)
 * Handles communication between content scripts and FYXERAI backend
 */

console.log('FYXERAI Background Script: Service worker started - Version 1.3.1 (Fixed Draft Generation)');

// Load configuration immediately on startup
loadConfiguration();

// Configuration
let FYXERAI_API_BASE = 'http://localhost:8000'; // Default development URL
const API_ENDPOINTS = {
    emails: '/api/emails/',
    health: '/api/extension/health/',
    triage: '/api/extension/triage/',
    reply: '/api/extension/reply/',
    meetings: '/api/meetings/summary/'
};

// Configuration management
async function loadConfiguration() {
    try {
        const result = await chrome.storage.sync.get(['apiEndpoint', 'isDevelopmentMode']);
        
        if (result.apiEndpoint) {
            FYXERAI_API_BASE = result.apiEndpoint;
        } else if (result.isDevelopmentMode !== false) {
            // Default to development mode
            FYXERAI_API_BASE = 'http://localhost:8000';
        } else {
            // Production mode (would be configured later)
            FYXERAI_API_BASE = 'https://api.fyxerai.com';
        }
        
        // Migrate old localhost ports to 8000
        if (FYXERAI_API_BASE.startsWith('http://localhost:8001') || FYXERAI_API_BASE.startsWith('http://localhost:8002')) {
            await saveConfiguration('http://localhost:8000', true);
        }
        
        console.log(`FYXERAI Background: Using API endpoint: ${FYXERAI_API_BASE}`);
    } catch (error) {
        console.warn('FYXERAI Background: Failed to load configuration:', error);
        // Fall back to default development endpoint
        FYXERAI_API_BASE = 'http://localhost:8000';
    }
}

async function saveConfiguration(apiEndpoint, isDevelopmentMode = true) {
    try {
        await chrome.storage.sync.set({
            apiEndpoint: apiEndpoint,
            isDevelopmentMode: isDevelopmentMode
        });
        FYXERAI_API_BASE = apiEndpoint;
        console.log(`FYXERAI Background: Configuration saved. API endpoint: ${FYXERAI_API_BASE}`);
    } catch (error) {
        console.error('FYXERAI Background: Failed to save configuration:', error);
    }
}

// Background script state
let extensionState = {
    connected: false,
    lastPing: null,
    emailsProcessed: 0,
    draftsCreated: 0
};

/**
 * Make API request with retry logic and better error handling
 * Uses a safe timeout implementation compatible across Chrome versions.
 */
async function makeAPIRequest(url, options, maxRetries = 3) {
    let lastError;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`FYXERAI Background: API request attempt ${attempt}/${maxRetries} to ${url}`);
            // Build fetch options and attach a safe timeout signal
            const fetchOptions = { ...options };

            // Safe timeout wrapper: prefer AbortSignal.timeout when available, otherwise fallback
            let timeoutId = null;
            let controller = null;
            try {
                if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
                    fetchOptions.signal = AbortSignal.timeout(30000);
                } else {
                    controller = new AbortController();
                    timeoutId = setTimeout(() => controller.abort(), 30000);
                    fetchOptions.signal = controller.signal;
                }
            } catch (e) {
                // As a last resort, skip setting a signal if environment lacks support
                console.warn('FYXERAI Background: Timeout signal unsupported, proceeding without abort controller');
            }

            const response = await fetch(url, fetchOptions);

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log(`FYXERAI Background: API request successful on attempt ${attempt}`);

            // Clear timeout if we set one
            if (timeoutId) clearTimeout(timeoutId);
            return result;

        } catch (error) {
            // Ensure any pending timeout is cleared if an error occurs
            try { if (typeof timeoutId !== 'undefined' && timeoutId) clearTimeout(timeoutId); } catch (_) {}
            lastError = error;
            console.warn(`FYXERAI Background: API request failed (attempt ${attempt}/${maxRetries}):`, error.message);
            
            // Don't retry on certain errors
            if (error.name === 'AbortError' || 
                error.message.includes('400') || 
                error.message.includes('401') || 
                error.message.includes('403')) {
                throw error;
            }
            
            // Wait before retry (exponential backoff)
            if (attempt < maxRetries) {
                const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
                console.log(`FYXERAI Background: Waiting ${delay}ms before retry...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }
    
    throw new Error(`API request failed after ${maxRetries} attempts: ${lastError.message}`);
}

/**
 * Message handler for communication with content scripts
 */
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('FYXERAI Background: Received message:', request);

    switch (request.action) {
        case 'triageInbox':
            handleTriageInbox(request, sender, sendResponse);
            return true; // Keep message channel open for async response

        case 'generateDrafts':
            handleGenerateDrafts(request, sender, sendResponse);
            return true;

        case 'generateAIDraft':
            handleGenerateAIDraft(request, sender, sendResponse);
            return true;

        case 'checkConnection':
            handleCheckConnection(request, sender, sendResponse);
            return true;

        case 'getStats':
            sendResponse({
                success: true,
                stats: {
                    emailsProcessed: extensionState.emailsProcessed,
                    draftsCreated: extensionState.draftsCreated,
                    connected: extensionState.connected
                }
            });
            break;

        case 'getConfiguration':
            chrome.storage.sync.get(['apiEndpoint', 'isDevelopmentMode'], (result) => {
                sendResponse({
                    success: true,
                    apiEndpoint: result.apiEndpoint || FYXERAI_API_BASE,
                    isDevelopmentMode: result.isDevelopmentMode !== false
                });
            });
            return true;

        case 'setConfiguration':
            saveConfiguration(request.apiEndpoint, request.isDevelopmentMode);
            sendResponse({ success: true });
            break;

        default:
            console.warn('FYXERAI Background: Unknown action:', request.action);
            sendResponse({ success: false, error: 'Unknown action' });
    }
});

/**
 * Handle inbox triage request
 */
async function handleTriageInbox(request, sender, sendResponse) {
    console.log('FYXERAI Background: Processing inbox triage...');
    
    try {
        // Get email data from content script's platform
        const emailData = await extractEmailsFromTab(sender.tab.id, request.platform);
        
        if (!emailData || emailData.length === 0) {
            throw new Error('No emails found to triage');
        }
        
        console.log(`FYXERAI Background: Triaging ${emailData.length} emails`);
        
        // Send to FYXERAI backend for triage with retry logic
        const result = await makeAPIRequest(`${FYXERAI_API_BASE}${API_ENDPOINTS.triage}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Extension-Source': 'fyxerai-chrome'
            },
            body: JSON.stringify({
                platform: request.platform,
                emails: emailData,
                action: 'batch_triage'
            })
        });
        
        // Update statistics
        extensionState.emailsProcessed += result.processed || 0;
        
        // Send categorization results back to content script
        chrome.tabs.sendMessage(sender.tab.id, {
            action: 'updateCategories',
            categories: result.categories
        });

        sendResponse({
            success: true,
            processed: result.processed,
            categories: result.categories,
            message: `Successfully triaged ${result.processed} emails`
        });

        console.log('FYXERAI Background: Triage completed:', result);

    } catch (error) {
        console.error('FYXERAI Background: Triage failed:', error);
        sendResponse({
            success: false,
            error: error.message,
            details: error.stack
        });
    }
}

/**
 * Handle draft generation request
 */
async function handleGenerateDrafts(request, sender, sendResponse) {
    console.log('FYXERAI Background: Generating drafts...');
    
    try {
        // Get emails that need replies
        const emailData = await extractEmailsFromTab(sender.tab.id, request.platform);
        
        // Filter emails that need replies (urgent/important categories)
        const replyEmails = emailData.filter(email => 
            ['urgent', 'important'].includes(email.category)
        );

        if (replyEmails.length === 0) {
            console.log('FYXERAI Background: No urgent/important emails found for draft generation - Version 1.3.1 Fix Applied');
            sendResponse({
                success: true,
                created: 0,
                drafts: [],
                message: 'No urgent or important emails found. Triage emails first to categorize them.'
            });
            return;
        }

        console.log(`FYXERAI Background: Generating drafts for ${replyEmails.length} emails`);

        const result = await makeAPIRequest(`${FYXERAI_API_BASE}${API_ENDPOINTS.reply}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Extension-Source': 'fyxerai-chrome'
            },
            body: JSON.stringify({
                platform: request.platform,
                emails: replyEmails,
                action: 'generate_drafts'
            })
        });
        
        // Update statistics
        extensionState.draftsCreated += result.created || 0;

        sendResponse({
            success: true,
            created: result.created,
            drafts: result.drafts,
            message: `Generated ${result.created} drafts successfully`
        });

        console.log('FYXERAI Background: Drafts generated:', result);

    } catch (error) {
        console.error('FYXERAI Background: Draft generation failed:', error);
        sendResponse({
            success: false,
            error: error.message,
            details: error.stack
        });
    }
}

/**
 * Handle single AI draft generation
 */
async function handleGenerateAIDraft(request, sender, sendResponse) {
    console.log('FYXERAI Background: Generating single AI draft...');
    
    try {
        if (!request.emailContent || (!request.emailContent.subject && !request.emailContent.body)) {
            throw new Error('Email content is required for draft generation');
        }

        const result = await makeAPIRequest(`${FYXERAI_API_BASE}${API_ENDPOINTS.reply}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Extension-Source': 'fyxerai-chrome'
            },
            body: JSON.stringify({
                platform: request.platform,
                email_content: request.emailContent,
                action: 'generate_single_draft'
            })
        });
        
        // Update statistics
        extensionState.draftsCreated += 1;

        sendResponse({
            success: true,
            draft: result.draft,
            message: 'AI draft generated successfully'
        });

        console.log('FYXERAI Background: Single draft generated');

    } catch (error) {
        console.error('FYXERAI Background: Single draft generation failed:', error);
        sendResponse({
            success: false,
            error: error.message,
            details: error.stack
        });
    }
}

/**
 * Handle connection check
 */
async function handleCheckConnection(request, sender, sendResponse) {
    try {
        console.log('FYXERAI Background: Testing connection to backend...');
        
        const result = await makeAPIRequest(`${FYXERAI_API_BASE}${API_ENDPOINTS.health}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Extension-Source': 'fyxerai-chrome'
            }
        }, 1); // Only 1 retry for health check

        extensionState.connected = true;
        extensionState.lastPing = new Date().toISOString();

        sendResponse({
            success: true,
            connected: true,
            status: result.status,
            message: result.message,
            timestamp: result.timestamp
        });

        console.log('FYXERAI Background: Connection check successful');

    } catch (error) {
        extensionState.connected = false;
        console.error('FYXERAI Background: Connection check failed:', error);
        
        sendResponse({
            success: false,
            connected: false,
            error: error.message,
            details: error.stack
        });
    }
}

/**
 * Extract email data from tab using content script
 */
async function extractEmailsFromTab(tabId, platform) {
    return new Promise((resolve, reject) => {
        // First check if tab still exists
        chrome.tabs.get(tabId, (tab) => {
            if (chrome.runtime.lastError) {
                reject(new Error(`Tab ${tabId} not found: ${chrome.runtime.lastError.message}`));
                return;
            }

            // Send message with timeout
            const timeoutId = setTimeout(() => {
                reject(new Error('Content script response timeout'));
            }, 10000); // 10 second timeout

            chrome.tabs.sendMessage(tabId, {
                action: 'extractEmails',
                platform: platform
            }, (response) => {
                clearTimeout(timeoutId);
                
                if (chrome.runtime.lastError) {
                    // Content script might not be injected yet, try to inject
                    console.log('FYXERAI Background: Content script not responding, attempting injection...');
                    injectContentScript(tabId).then(() => {
                        // Retry after injection
                        setTimeout(() => {
                            chrome.tabs.sendMessage(tabId, {
                                action: 'extractEmails',
                                platform: platform
                            }, (retryResponse) => {
                                if (chrome.runtime.lastError) {
                                    reject(new Error(`Content script injection failed: ${chrome.runtime.lastError.message}`));
                                } else if (retryResponse && retryResponse.success) {
                                    resolve(retryResponse.emails || []);
                                } else {
                                    reject(new Error('Failed to extract emails after injection'));
                                }
                            });
                        }, 1000);
                    }).catch(error => {
                        reject(new Error(`Content script injection failed: ${error.message}`));
                    });
                } else if (response && response.success) {
                    resolve(response.emails || []);
                } else {
                    reject(new Error('Failed to extract emails from page'));
                }
            });
        });
    });
}

/**
 * Inject content script into tab if not already present
 */
async function injectContentScript(tabId) {
    return new Promise((resolve, reject) => {
        chrome.scripting.executeScript({
            target: { tabId: tabId },
            files: ['content.js']
        }, (results) => {
            if (chrome.runtime.lastError) {
                reject(new Error(chrome.runtime.lastError.message));
            } else {
                resolve(results);
            }
        });
    });
}

/**
 * Periodic connection check
 */
function startPeriodicHealthCheck() {
    setInterval(async () => {
        try {
            const result = await makeAPIRequest(`${FYXERAI_API_BASE}${API_ENDPOINTS.health}`, {
                method: 'GET',
                headers: {
                    'X-Extension-Source': 'fyxerai-chrome'
                }
            }, 1); // Single retry for health check
            
            const wasConnected = extensionState.connected;
            extensionState.connected = true;
            extensionState.lastPing = new Date().toISOString();

            // Notify content scripts of connection status change
            if (wasConnected !== extensionState.connected) {
                console.log('FYXERAI Background: Connection restored');
                notifyContentScriptsOfConnectionChange(true);
            }

        } catch (error) {
            const wasConnected = extensionState.connected;
            extensionState.connected = false;
            
            // Only log as warning every 5 minutes to avoid spam
            if (Date.now() % (5 * 60 * 1000) < 30000) {
                console.warn('FYXERAI Background: Periodic health check failed:', error.message);
            }
            
            // Notify content scripts of connection loss
            if (wasConnected !== extensionState.connected) {
                console.log('FYXERAI Background: Connection lost');
                notifyContentScriptsOfConnectionChange(false);
            }
        }
    }, 30000); // Check every 30 seconds
}

/**
 * Notify content scripts of connection status change
 */
function notifyContentScriptsOfConnectionChange(connected) {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        tabs.forEach(tab => {
            if (tab.url?.includes('mail.google.com') || 
                tab.url?.includes('outlook')) {
                chrome.tabs.sendMessage(tab.id, {
                    action: 'connectionStatusChanged',
                    connected: connected
                }, (response) => {
                    if (chrome.runtime.lastError) {
                        // Content script might not be loaded, ignore error
                    }
                });
            }
        });
    });
}

/**
 * Handle extension installation
 */
chrome.runtime.onInstalled.addListener(async (details) => {
    console.log('FYXERAI Background: Extension installed/updated');
    
    // Load configuration first
    await loadConfiguration();
    
    if (details.reason === 'install') {
        // First-time installation
        console.log('FYXERAI Background: First installation detected');
        
        // Open welcome page
        chrome.tabs.create({
            url: `${FYXERAI_API_BASE}/components/`
        });
    }
    
    // Create context menus
    chrome.contextMenus.create({
        id: 'fyxerai-categorize',
        title: 'Categorize with FYXERAI',
        contexts: ['selection'],
        documentUrlPatterns: [
            '*://mail.google.com/*',
            '*://outlook.live.com/*',
            '*://outlook.office.com/*'
        ]
    });

    chrome.contextMenus.create({
        id: 'fyxerai-generate-reply',
        title: 'Generate AI Reply',
        contexts: ['selection'],
        documentUrlPatterns: [
            '*://mail.google.com/*',
            '*://outlook.live.com/*',
            '*://outlook.office.com/*'
        ]
    });
    
    // Start health monitoring
    startPeriodicHealthCheck();
});

/**
 * Handle extension startup
 */
chrome.runtime.onStartup.addListener(async () => {
    console.log('FYXERAI Background: Extension started');
    
    // Load configuration
    await loadConfiguration();
    
    startPeriodicHealthCheck();
});

/**
 * Handle tab updates to inject content scripts
 */
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        const isGmail = tab.url.includes('mail.google.com');
        const isOutlook = tab.url.includes('outlook');
        
        if (isGmail || isOutlook) {
            console.log(`FYXERAI Background: Email platform detected on tab ${tabId}`);
            
            // Wait a bit for page to fully load, then inject content script
            setTimeout(async () => {
                try {
                    // First try to ping existing content script
                    const pingResponse = await new Promise((resolve) => {
                        chrome.tabs.sendMessage(tabId, { action: 'ping' }, (response) => {
                            if (chrome.runtime.lastError) {
                                resolve(null);
                            } else {
                                resolve(response);
                            }
                        });
                    });

                    if (!pingResponse) {
                        // Content script not responding, inject it
                        console.log(`FYXERAI Background: Injecting content script into tab ${tabId}`);
                        await injectContentScript(tabId);
                        
                        // Wait for injection to complete
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }

                    // Send initialization message
                    chrome.tabs.sendMessage(tabId, {
                        action: 'initialize',
                        platform: isGmail ? 'gmail' : 'outlook',
                        apiBase: FYXERAI_API_BASE
                    }, (response) => {
                        if (chrome.runtime.lastError) {
                            console.warn('FYXERAI Background: Init message failed:', chrome.runtime.lastError.message);
                        } else {
                            console.log(`FYXERAI Background: Successfully initialized tab ${tabId}`);
                        }
                    });
                } catch (error) {
                    console.warn('FYXERAI Background: Tab initialization failed:', error);
                }
            }, 3000); // Increased delay to ensure page is fully loaded
        }
    }
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    switch (info.menuItemId) {
        case 'fyxerai-categorize':
            chrome.tabs.sendMessage(tab.id, {
                action: 'categorizeSelection',
                selectedText: info.selectionText
            });
            break;
            
        case 'fyxerai-generate-reply':
            chrome.tabs.sendMessage(tab.id, {
                action: 'generateReplyForSelection',
                selectedText: info.selectionText
            });
            break;
    }
});

console.log('FYXERAI Background Script: Initialized successfully');
