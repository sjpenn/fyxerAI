/**
 * FYXERAI Chrome Extension - Popup Script
 * Handles popup interface interactions and communication with background script
 */

console.log('FYXERAI Popup: Script loaded');

// DOM elements
const elements = {
    connectionStatus: document.getElementById('connectionStatus'),
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText'),
    emailsProcessed: document.getElementById('emailsProcessed'),
    draftsCreated: document.getElementById('draftsCreated'),
    timesSaved: document.getElementById('timesSaved'),
    triageInboxBtn: document.getElementById('triageInboxBtn'),
    generateDraftsBtn: document.getElementById('generateDraftsBtn'),
    openDashboardBtn: document.getElementById('openDashboardBtn'),
    activityList: document.getElementById('activityList'),
    autoTriageEnabled: document.getElementById('autoTriageEnabled'),
    notificationsEnabled: document.getElementById('notificationsEnabled'),
    draftTone: document.getElementById('draftTone'),
    developmentModeEnabled: document.getElementById('developmentModeEnabled'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText'),
    messageContainer: document.getElementById('messageContainer'),
    messageContent: document.getElementById('messageContent'),
    messageClose: document.getElementById('messageClose'),
    settingsLink: document.getElementById('settingsLink'),
    helpLink: document.getElementById('helpLink'),
    feedbackLink: document.getElementById('feedbackLink')
};

// Application state
let appState = {
    connected: false,
    currentTab: null,
    platform: null,
    stats: {
        emailsProcessed: 0,
        draftsCreated: 0,
        timesSaved: 0
    },
    settings: {
        autoTriageEnabled: true,
        notificationsEnabled: true,
        draftTone: 'professional',
        developmentModeEnabled: true
    },
    configuration: {
        apiEndpoint: 'http://localhost:8000',
        isDevelopmentMode: true
    }
};

/**
 * Initialize popup when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('FYXERAI Popup: Initializing...');
    
    // Load settings and configuration
    await loadSettings();
    await loadConfiguration();
    
    // Get current tab info
    await getCurrentTabInfo();
    
    // Check connection status
    await checkConnectionStatus();
    
    // Load statistics
    await loadStatistics();
    
    // Set up event listeners
    setupEventListeners();
    
    // Update UI
    updateUI();
    
    console.log('FYXERAI Popup: Initialization complete');
});

/**
 * Load configuration from background script
 */
async function loadConfiguration() {
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'getConfiguration'
        });
        
        if (response && response.success) {
            appState.configuration.apiEndpoint = response.apiEndpoint;
            appState.configuration.isDevelopmentMode = response.isDevelopmentMode;
            
            console.log('FYXERAI Popup: Configuration loaded:', appState.configuration);
        }
    } catch (error) {
        console.error('FYXERAI Popup: Failed to load configuration:', error);
    }
}

/**
 * Load saved settings from storage
 */
async function loadSettings() {
    try {
        const result = await chrome.storage.sync.get([
            'autoTriageEnabled',
            'notificationsEnabled', 
            'draftTone',
            'isDevelopmentMode'
        ]);
        
        if (result.autoTriageEnabled !== undefined) {
            appState.settings.autoTriageEnabled = result.autoTriageEnabled;
            elements.autoTriageEnabled.checked = result.autoTriageEnabled;
        }
        
        if (result.notificationsEnabled !== undefined) {
            appState.settings.notificationsEnabled = result.notificationsEnabled;
            elements.notificationsEnabled.checked = result.notificationsEnabled;
        }
        
        if (result.isDevelopmentMode !== undefined) {
            appState.settings.developmentModeEnabled = result.isDevelopmentMode;
            elements.developmentModeEnabled.checked = result.isDevelopmentMode;
        }
        
        if (result.draftTone) {
            appState.settings.draftTone = result.draftTone;
            elements.draftTone.value = result.draftTone;
        }
        
        console.log('FYXERAI Popup: Settings loaded:', appState.settings);
    } catch (error) {
        console.error('FYXERAI Popup: Failed to load settings:', error);
    }
}

/**
 * Get current tab information
 */
async function getCurrentTabInfo() {
    try {
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs.length > 0) {
            appState.currentTab = tabs[0];
            
            // Detect platform
            if (tabs[0].url.includes('mail.google.com')) {
                appState.platform = 'gmail';
            } else if (tabs[0].url.includes('outlook')) {
                appState.platform = 'outlook';
            }
            
            console.log('FYXERAI Popup: Current tab:', {
                url: tabs[0].url,
                platform: appState.platform
            });
        }
    } catch (error) {
        console.error('FYXERAI Popup: Failed to get tab info:', error);
    }
}

/**
 * Check connection status with background script
 */
async function checkConnectionStatus() {
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'checkConnection'
        });
        
        appState.connected = response && response.connected;
        updateConnectionStatus();
        
    } catch (error) {
        console.error('FYXERAI Popup: Connection check failed:', error);
        appState.connected = false;
        updateConnectionStatus();
    }
}

/**
 * Load statistics from background script
 */
async function loadStatistics() {
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'getStats'
        });
        
        if (response && response.success) {
            appState.stats = response.stats;
            updateStatistics();
        }
        
    } catch (error) {
        console.error('FYXERAI Popup: Failed to load statistics:', error);
    }
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Action buttons
    elements.triageInboxBtn.addEventListener('click', handleTriageInbox);
    elements.generateDraftsBtn.addEventListener('click', handleGenerateDrafts);
    elements.openDashboardBtn.addEventListener('click', handleOpenDashboard);
    
    // Settings
    elements.autoTriageEnabled.addEventListener('change', handleSettingChange);
    elements.notificationsEnabled.addEventListener('change', handleSettingChange);
    elements.draftTone.addEventListener('change', handleSettingChange);
    elements.developmentModeEnabled.addEventListener('change', handleDevelopmentModeChange);
    
    // Message close
    elements.messageClose.addEventListener('click', hideMessage);
    
    // Footer links
    elements.settingsLink.addEventListener('click', handleOpenSettings);
    elements.helpLink.addEventListener('click', handleOpenHelp);
    elements.feedbackLink.addEventListener('click', handleOpenFeedback);
    
    console.log('FYXERAI Popup: Event listeners set up');
}

/**
 * Handle triage inbox action
 */
async function handleTriageInbox() {
    if (!appState.currentTab || !appState.platform) {
        showMessage('Please navigate to Gmail or Outlook first', 'error');
        return;
    }
    
    showLoading('Triaging inbox...');
    
    try {
        const response = await chrome.tabs.sendMessage(appState.currentTab.id, {
            action: 'triageInbox',
            platform: appState.platform
        });
        
        hideLoading();
        
        if (response && response.success) {
            showMessage(`Successfully triaged ${response.processed} emails`, 'success');
            appState.stats.emailsProcessed += response.processed;
            updateStatistics();
        } else {
            showMessage('Failed to triage inbox', 'error');
        }
        
    } catch (error) {
        hideLoading();
        console.error('FYXERAI Popup: Triage failed:', error);
        showMessage('Failed to triage inbox', 'error');
    }
}

/**
 * Handle generate drafts action
 */
async function handleGenerateDrafts() {
    if (!appState.currentTab || !appState.platform) {
        showMessage('Please navigate to Gmail or Outlook first', 'error');
        return;
    }
    
    showLoading('Generating AI drafts...');
    
    try {
        const response = await chrome.tabs.sendMessage(appState.currentTab.id, {
            action: 'generateDrafts',
            platform: appState.platform
        });
        
        hideLoading();
        
        if (response && response.success) {
            showMessage(`Successfully generated ${response.created} drafts`, 'success');
            appState.stats.draftsCreated += response.created;
            updateStatistics();
        } else {
            showMessage('Failed to generate drafts', 'error');
        }
        
    } catch (error) {
        hideLoading();
        console.error('FYXERAI Popup: Draft generation failed:', error);
        showMessage('Failed to generate drafts', 'error');
    }
}

/**
 * Handle open dashboard action
 */
function handleOpenDashboard() {
    chrome.tabs.create({
        url: 'http://localhost:8000/'
    });
    window.close();
}

/**
 * Handle setting changes
 */
async function handleSettingChange(event) {
    const setting = event.target.id;
    let value;
    
    if (event.target.type === 'checkbox') {
        value = event.target.checked;
    } else {
        value = event.target.value;
    }
    
    appState.settings[setting] = value;
    
    // Save to storage
    try {
        await chrome.storage.sync.set({ [setting]: value });
        console.log('FYXERAI Popup: Setting saved:', setting, value);
    } catch (error) {
        console.error('FYXERAI Popup: Failed to save setting:', error);
    }
}

/**
 * Handle development mode toggle
 */
async function handleDevelopmentModeChange(event) {
    const isDevelopmentMode = event.target.checked;
    
    // Update state
    appState.settings.developmentModeEnabled = isDevelopmentMode;
    appState.configuration.isDevelopmentMode = isDevelopmentMode;
    
    // Determine API endpoint
    const apiEndpoint = isDevelopmentMode ? 'http://localhost:8000' : 'https://api.fyxerai.com';
    appState.configuration.apiEndpoint = apiEndpoint;
    
    try {
        // Save configuration to background script
        await chrome.runtime.sendMessage({
            action: 'setConfiguration',
            apiEndpoint: apiEndpoint,
            isDevelopmentMode: isDevelopmentMode
        });
        
        // Save to storage
        await chrome.storage.sync.set({ isDevelopmentMode: isDevelopmentMode });
        
        console.log('FYXERAI Popup: Development mode changed:', isDevelopmentMode, 'API:', apiEndpoint);
        
        // Show feedback message
        showMessage(
            `Switched to ${isDevelopmentMode ? 'development' : 'production'} mode (${apiEndpoint})`, 
            'success'
        );
        
        // Recheck connection with new endpoint
        setTimeout(() => {
            checkConnectionStatus();
        }, 1000);
        
    } catch (error) {
        console.error('FYXERAI Popup: Failed to change development mode:', error);
        showMessage('Failed to change development mode', 'error');
        
        // Revert the checkbox
        event.target.checked = !isDevelopmentMode;
    }
}

/**
 * Handle footer link clicks
 */
function handleOpenSettings() {
    chrome.tabs.create({
        url: 'http://localhost:8000/components/'
    });
    window.close();
}

function handleOpenHelp() {
    chrome.tabs.create({
        url: 'https://github.com/fyxerai/chrome-extension'
    });
    window.close();
}

function handleOpenFeedback() {
    chrome.tabs.create({
        url: 'mailto:support@fyxerai.com?subject=Chrome Extension Feedback'
    });
    window.close();
}

/**
 * Update UI based on current state
 */
function updateUI() {
    updateConnectionStatus();
    updateStatistics();
    updatePlatformState();
}

/**
 * Update connection status display
 */
function updateConnectionStatus() {
    if (appState.connected) {
        elements.statusDot.className = 'fyxerai-status-dot fyxerai-status-connected';
        elements.statusText.textContent = 'Connected';
        elements.connectionStatus.title = 'Connected to FYXERAI backend';
    } else {
        elements.statusDot.className = 'fyxerai-status-dot fyxerai-status-disconnected';
        elements.statusText.textContent = 'Disconnected';
        elements.connectionStatus.title = 'Cannot connect to FYXERAI backend';
    }
}

/**
 * Update statistics display
 */
function updateStatistics() {
    elements.emailsProcessed.textContent = appState.stats.emailsProcessed || 0;
    elements.draftsCreated.textContent = appState.stats.draftsCreated || 0;
    
    // Calculate time saved (rough estimate: 2 minutes per email + 5 minutes per draft)
    const timeSaved = (appState.stats.emailsProcessed * 2 + appState.stats.draftsCreated * 5) / 60;
    elements.timesSaved.textContent = `${timeSaved.toFixed(1)}h`;
}

/**
 * Update UI based on detected platform
 */
function updatePlatformState() {
    const isEmailPlatform = appState.platform === 'gmail' || appState.platform === 'outlook';
    
    elements.triageInboxBtn.disabled = !isEmailPlatform || !appState.connected;
    elements.generateDraftsBtn.disabled = !isEmailPlatform || !appState.connected;
    
    if (!isEmailPlatform) {
        showMessage('Navigate to Gmail or Outlook to use FYXERAI features', 'info');
    } else if (!appState.connected) {
        showMessage('Cannot connect to FYXERAI backend', 'error');
    }
}

/**
 * Show loading overlay
 */
function showLoading(text = 'Processing...') {
    elements.loadingText.textContent = text;
    elements.loadingOverlay.style.display = 'flex';
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    elements.loadingOverlay.style.display = 'none';
}

/**
 * Show message to user
 */
function showMessage(text, type = 'info') {
    elements.messageContent.textContent = text;
    elements.messageContainer.className = `fyxerai-message fyxerai-message-${type}`;
    elements.messageContainer.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(hideMessage, 5000);
}

/**
 * Hide message
 */
function hideMessage() {
    elements.messageContainer.style.display = 'none';
}

console.log('FYXERAI Popup: Script initialized');
