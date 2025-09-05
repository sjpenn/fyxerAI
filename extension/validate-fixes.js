/**
 * Quick validation script for Chrome extension fixes
 * Run this in browser console to check if fixes work
 */

console.log('🔧 FYXERAI Extension Validation Script');

// Check 1: CSP TrustedTypes compliance
console.log('\n1. Checking CSP TrustedTypes compliance...');
if (window.trustedTypes) {
    try {
        const testPolicy = trustedTypes.createPolicy('test-fyxerai', {
            createHTML: string => string,
            createScript: string => string,
            createScriptURL: string => string
        });
        console.log('✅ TrustedTypes policy creation works');
        
        // Test safe innerHTML assignment
        const testDiv = document.createElement('div');
        testDiv.innerHTML = testPolicy.createHTML('<span>Test content</span>');
        console.log('✅ Safe innerHTML assignment works');
    } catch (error) {
        console.error('❌ TrustedTypes error:', error);
    }
} else {
    console.log('ℹ️ TrustedTypes not available in this browser');
}

// Check 2: Extension APIs
console.log('\n2. Checking Extension APIs...');
if (typeof chrome !== 'undefined' && chrome.runtime) {
    console.log('✅ Chrome extension APIs available');
    console.log('   Extension ID:', chrome.runtime.id);
    console.log('   Manifest:', chrome.runtime.getManifest()?.manifest_version);
} else {
    console.log('ℹ️ Extension APIs not available (not in extension context)');
}

// Check 3: Gmail selectors (if on Gmail)
console.log('\n3. Checking Gmail selectors...');
if (window.location.hostname === 'mail.google.com') {
    const emailElements = document.querySelectorAll('tr[data-thread-id]:not([data-fyxerai-processed])');
    console.log(`✅ Found ${emailElements.length} unprocessed Gmail email elements`);
    
    // Test our improved selector
    const duplicateCheck = document.querySelectorAll('tr[data-thread-id]');
    const threadIds = new Set();
    let duplicates = 0;
    
    duplicateCheck.forEach(el => {
        const threadId = el.getAttribute('data-thread-id');
        if (threadIds.has(threadId)) {
            duplicates++;
        } else {
            threadIds.add(threadId);
        }
    });
    
    console.log(`ℹ️ Duplicate threads found: ${duplicates}`);
    console.log(`ℹ️ Unique threads: ${threadIds.size}`);
} else {
    console.log('ℹ️ Not on Gmail - skipping Gmail-specific checks');
}

// Check 4: DOM manipulation without innerHTML
console.log('\n4. Testing safe DOM manipulation...');
try {
    const testContainer = document.createElement('div');
    testContainer.id = 'fyxerai-test-container';
    
    // Old way (problematic with CSP)
    // testContainer.innerHTML = '<span>Test</span>';
    
    // New way (CSP compliant)
    while (testContainer.firstChild) {
        testContainer.removeChild(testContainer.firstChild);
    }
    
    const testSpan = document.createElement('span');
    testSpan.textContent = 'Test content';
    testContainer.appendChild(testSpan);
    
    console.log('✅ Safe DOM manipulation works');
    testContainer.remove(); // Clean up
} catch (error) {
    console.error('❌ DOM manipulation error:', error);
}

console.log('\n🎉 Validation complete! Check results above.');