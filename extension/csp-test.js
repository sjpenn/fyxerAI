/**
 * FYXERAI Extension - CSP Compliance Test Script
 * Tests that the extension works with Gmail's Trusted Types requirements
 */

console.log('FYXERAI CSP Test: Starting compliance test...');

// Test 1: Check if Trusted Types are available
console.log('Test 1: Trusted Types Support');
if (window.trustedTypes) {
    console.log('✅ Trusted Types API is available');
    
    // Test policy creation
    try {
        const testPolicy = window.trustedTypes.createPolicy('fyxerai-test', {
            createHTML: (string) => string
        });
        console.log('✅ Can create Trusted Types policy');
        
        // Test HTML creation
        const testDiv = document.createElement('div');
        testDiv.innerHTML = testPolicy.createHTML('<span>Test content</span>');
        console.log('✅ Can create TrustedHTML');
        
    } catch (error) {
        console.error('❌ Trusted Types policy creation failed:', error);
    }
} else {
    console.log('⚠️  Trusted Types API not available (may not be required)');
}

// Test 2: Check DOM manipulation compliance
console.log('Test 2: DOM Manipulation');
try {
    const testElement = document.createElement('div');
    testElement.className = 'fyxerai-test';
    testElement.textContent = 'Test content';
    console.log('✅ Can create elements with textContent');
    
    // Test event listeners
    testElement.addEventListener('click', () => {
        console.log('Event listener test successful');
    });
    console.log('✅ Can add event listeners');
    
} catch (error) {
    console.error('❌ DOM manipulation failed:', error);
}

// Test 3: Check Chrome extension APIs
console.log('Test 3: Chrome Extension APIs');
if (chrome && chrome.runtime) {
    console.log('✅ Chrome extension runtime available');
    
    try {
        chrome.runtime.sendMessage({action: 'test'}, (response) => {
            console.log('Extension messaging test:', response ? '✅' : '⚠️');
        });
    } catch (error) {
        console.error('❌ Extension messaging failed:', error);
    }
} else {
    console.error('❌ Chrome extension APIs not available');
}

console.log('FYXERAI CSP Test: Test suite completed');