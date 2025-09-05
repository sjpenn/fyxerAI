#!/usr/bin/env node

/**
 * Simple OAuth flow test to capture Google's OAuth consent screen
 * This will show us what app name Google displays
 */

const puppeteer = require('puppeteer');

async function testOAuthFlow() {
    const browser = await puppeteer.launch({
        headless: false,
        slowMo: 500,
        args: ['--no-sandbox', '--disable-web-security']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1366, height: 768 });

    try {
        console.log('🔐 Testing OAuth Flow...');
        
        // Navigate directly to the OAuth login endpoint
        const baseUrl = 'http://localhost:8001';
        await page.goto(`${baseUrl}/auth/google/login/`, {
            waitUntil: 'networkidle2',
            timeout: 10000
        });

        console.log(`📍 Current URL: ${page.url()}`);

        // Check if we were redirected to Google
        if (page.url().includes('accounts.google.com')) {
            console.log('✅ Successfully redirected to Google OAuth');
            
            // Wait for the page to load completely
            await page.waitForTimeout(3000);
            
            // Take a screenshot of the OAuth consent screen
            await page.screenshot({ 
                path: 'oauth_consent_screen_full.png', 
                fullPage: true 
            });
            console.log('📸 Screenshot saved: oauth_consent_screen_full.png');

            // Try to find the app name in various possible selectors
            const possibleSelectors = [
                '[data-app-name]',
                '[data-test-id="app-name"]',
                'h1',
                'h2',
                '.PrDSKc', // Google's app name class (may change)
                '[jsname="r4nke"]', // Another possible class
                '.title',
                '.oauth-title'
            ];

            const appInfo = await page.evaluate((selectors) => {
                const results = [];
                
                // Check all possible selectors
                selectors.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            if (el.textContent.trim()) {
                                results.push({
                                    selector,
                                    text: el.textContent.trim()
                                });
                            }
                        });
                    } catch (e) {
                        // Ignore invalid selectors
                    }
                });

                // Also get page title
                results.push({
                    selector: 'title',
                    text: document.title
                });

                // Get all visible text to search for project names
                const allText = document.body.innerText || document.body.textContent || '';
                const blackCoralMatch = allText.match(/black coral/i);
                const fyxeraiMatch = allText.match(/fyxer|fyxerai/i);

                return {
                    elements: results,
                    containsBlackCoral: !!blackCoralMatch,
                    containsFyxerai: !!fyxeraiMatch,
                    allText: allText.slice(0, 500) // First 500 chars for analysis
                };
            }, possibleSelectors);

            console.log('\n📊 OAuth Consent Screen Analysis:');
            console.log('═'.repeat(50));

            if (appInfo.containsBlackCoral) {
                console.log('⚠️  WARNING: "Black Coral" found in OAuth consent screen');
                console.log('   Your Google Cloud OAuth app still shows the old name');
            } else {
                console.log('✅ No "Black Coral" references found');
            }

            if (appInfo.containsFyxerai) {
                console.log('✅ FYXERAI references found in consent screen');
            } else {
                console.log('❌ No FYXERAI references found');
            }

            console.log('\n🔍 Text Elements Found:');
            appInfo.elements.forEach(el => {
                if (el.text.length > 0 && el.text.length < 100) {
                    console.log(`   ${el.selector}: ${el.text}`);
                }
            });

            console.log('\n📄 Page Text Sample:');
            console.log(appInfo.allText);

            // Save detailed report
            const report = {
                timestamp: new Date().toISOString(),
                url: page.url(),
                analysis: appInfo,
                recommendations: []
            };

            if (appInfo.containsBlackCoral) {
                report.recommendations = [
                    'Update OAuth app name in Google Cloud Console',
                    'Go to https://console.cloud.google.com/apis/credentials',
                    'Edit your OAuth 2.0 Client ID',
                    'Change the name from "Black Coral" to "FYXERAI" or similar'
                ];
            }

            require('fs').writeFileSync('oauth_analysis_report.json', JSON.stringify(report, null, 2));
            console.log('\n📄 Detailed report saved: oauth_analysis_report.json');

            return report;

        } else {
            console.log('❌ Not redirected to Google OAuth');
            console.log(`   Current URL: ${page.url()}`);
            
            // Take screenshot of error page
            await page.screenshot({ path: 'oauth_error.png' });
            console.log('📸 Error screenshot saved: oauth_error.png');
            
            return null;
        }

    } catch (error) {
        console.error('❌ Test failed:', error.message);
        
        // Take screenshot on error
        try {
            await page.screenshot({ path: 'oauth_test_error.png' });
            console.log('📸 Error screenshot saved: oauth_test_error.png');
        } catch (screenshotError) {
            // Ignore screenshot errors
        }
        
        return null;
    } finally {
        await browser.close();
        console.log('🧹 Browser closed');
    }
}

// Run the test
testOAuthFlow().then(result => {
    if (result) {
        if (result.analysis.containsBlackCoral) {
            console.log('\n🎯 CONCLUSION: OAuth app name needs to be updated in Google Cloud Console');
            process.exit(1);
        } else {
            console.log('\n🎯 CONCLUSION: OAuth app name appears to be correctly configured');
            process.exit(0);
        }
    } else {
        console.log('\n🎯 CONCLUSION: Could not complete OAuth flow test');
        process.exit(1);
    }
});