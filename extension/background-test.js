/**
 * FYXERAI Chrome Extension - Minimal Background Script for Testing
 */

console.log('FYXERAI Background Script: Service worker started');

// Configuration
const FYXERAI_API_BASE = 'http://localhost:8000';

// Simple message handler
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('FYXERAI Background: Received message:', request);
    sendResponse({ success: true, message: 'Background script is working' });
});

// Simple installation handler
chrome.runtime.onInstalled.addListener((details) => {
    console.log('FYXERAI Background: Extension installed/updated');
    
    // Create a simple context menu
    try {
        chrome.contextMenus.create({
            id: 'fyxerai-test',
            title: 'FYXERAI Test',
            contexts: ['page']
        });
        console.log('Context menu created successfully');
    } catch (error) {
        console.error('Context menu creation failed:', error);
    }
});

// Context menu click handler
chrome.contextMenus.onClicked.addListener((info, tab) => {
    console.log('Context menu clicked:', info.menuItemId);
});

console.log('FYXERAI Background Script: Initialized successfully');
