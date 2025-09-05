#!/usr/bin/env node

/**
 * OAuth test that handles authentication first, then tests the OAuth flow
 */

const puppeteer = require('puppeteer');

async function createUserAndLogin(page, baseUrl) {
    console.log('👤 Creating test user and logging in...');
    
    try {
        // Navigate to signup page
        await page.goto(`${baseUrl}/signup/`, { waitUntil: 'networkidle2' });
        
        // Fill out registration form
        await page.type('input[name="username"]', 'oauthtest');
        await page.type('input[name="email"]', 'test@fyxerai.com');
        await page.type('input[name="password1"]', 'TestPass123!');
        await page.type('input[name="password2"]', 'TestPass123!');
        
        // Submit form
        await page.click('button[type="submit"]');
        await page.waitForNavigation({ waitUntil: 'networkidle2' });
        
        console.log('✅ User created and logged in');
        return true;
        
    } catch (error) {
        console.log('⚠️  Signup failed, trying login instead...');
        
        // Try to login with existing credentials
        try {
            await page.goto(`${baseUrl}/login/`, { waitUntil: 'networkidle2' });
            await page.type('input[name="username"]', 'oauthtest');
            await page.type('input[name="password"]', 'TestPass123!');
            await page.click('button[type="submit"]');
            await page.waitForNavigation({ waitUntil: 'networkidle2' });
            
            console.log('✅ Logged in with existing user');
            return true;
            
        } catch (loginError) {
            console.error('❌ Login failed:', loginError.message);
            return false;
        }
    }
}

async function testAuthenticatedOAuthFlow() {
    const browser = await puppeteer.launch({
        headless: false,
        slowMo: 500,
        args: ['--no-sandbox', '--disable-web-security', '--disable-features=VizDisplayCompositor']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1366, height: 768 });

    try {
        const baseUrl = 'http://localhost:8001';
        
        // First authenticate
        const loginSuccess = await createUserAndLogin(page, baseUrl);
        if (!loginSuccess) {
            throw new Error('Authentication failed');
        }
        
        console.log('🔐 Testing OAuth flow with authenticated user...');
        
        // Now test OAuth flow
        await page.goto(`${baseUrl}/auth/gmail/login/`, {
            waitUntil: 'networkidle2',
            timeout: 10000
        });

        const currentUrl = page.url();
        console.log(`📍 Current URL: ${currentUrl}`);

        // Check if we were redirected to Google
        if (currentUrl.includes('accounts.google.com')) {
            console.log('✅ Successfully redirected to Google OAuth');
            
            // Wait for the page to load completely
            await page.waitForTimeout(3000);
            
            // Take a full screenshot
            await page.screenshot({ 
                path: 'google_oauth_consent_screen.png', 
                fullPage: true 
            });
            console.log('📸 Full screenshot saved: google_oauth_consent_screen.png');

            // Analyze the page content
            const pageAnalysis = await page.evaluate(() => {
                const pageText = document.body.innerText || document.body.textContent || '';
                
                // Look for various indicators
                const analysis = {
                    title: document.title,
                    url: window.location.href,
                    containsBlackCoral: /black coral/i.test(pageText),
                    containsFyxerai: /fyxer/i.test(pageText),
                    appNameElements: [],
                    fullText: pageText.substring(0, 1000) // First 1000 chars
                };

                // Try to find app name in common locations
                const selectors = [
                    '[data-app-name]',
                    '.PrDSKc', // Common Google class for app names
                    'h1', 'h2', 'h3',
                    '.oauth-title',
                    '.title',
                    '[role="heading"]'
                ];

                selectors.forEach(selector => {
                    try {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            if (el.textContent && el.textContent.trim().length > 0 && el.textContent.trim().length < 200) {
                                analysis.appNameElements.push({
                                    selector,
                                    text: el.textContent.trim(),
                                    visible: el.offsetParent !== null
                                });
                            }
                        });
                    } catch (e) {
                        // Ignore selector errors
                    }
                });

                return analysis;
            });

            console.log('\n🎯 OAUTH CONSENT SCREEN ANALYSIS:');
            console.log('═'.repeat(60));
            console.log(`📄 Title: ${pageAnalysis.title}`);
            console.log(`🔗 URL: ${pageAnalysis.url}`);
            
            if (pageAnalysis.containsBlackCoral) {
                console.log('❌ ISSUE FOUND: "Black Coral" text detected in consent screen');
                console.log('   This confirms your OAuth app still uses the old project name');
            } else {
                console.log('✅ No "Black Coral" references found');
            }

            if (pageAnalysis.containsFyxerai) {
                console.log('✅ "FYXERAI" or similar references found');
            } else {
                console.log('⚠️  No "FYXERAI" references detected');
            }

            console.log('\n🏷️  APP NAME ELEMENTS FOUND:');
            if (pageAnalysis.appNameElements.length > 0) {
                pageAnalysis.appNameElements.forEach((el, i) => {
                    const visibility = el.visible ? '👁️' : '🙈';
                    console.log(`   ${i + 1}. ${visibility} [${el.selector}]: "${el.text}"`);
                });
            } else {
                console.log('   No clear app name elements detected');
            }

            console.log('\n📝 PAGE TEXT SAMPLE:');
            console.log('-'.repeat(40));
            console.log(pageAnalysis.fullText);

            // Generate detailed report
            const report = {
                timestamp: new Date().toISOString(),
                testResult: 'success',
                oauthRedirectWorking: true,
                googleConsentScreenAnalysis: pageAnalysis,
                conclusions: [],
                recommendations: []
            };

            if (pageAnalysis.containsBlackCoral) {
                report.conclusions.push('OAuth app name still shows "Black Coral" in Google Cloud Console');
                report.recommendations.push('Update OAuth 2.0 Client ID name in Google Cloud Console');
                report.recommendations.push('Visit https://console.cloud.google.com/apis/credentials');
                report.recommendations.push('Edit your OAuth 2.0 Client ID and change name to FYXERAI');
            } else {
                report.conclusions.push('OAuth app name appears to be updated correctly');
            }

            // Save report
            require('fs').writeFileSync('oauth_detailed_analysis.json', JSON.stringify(report, null, 2));
            console.log('\n📄 Detailed analysis saved: oauth_detailed_analysis.json');

            return report;

        } else {
            console.log('❌ Not redirected to Google OAuth');
            console.log(`   Stayed on: ${currentUrl}`);
            
            // Check for errors on the current page
            const pageContent = await page.content();
            console.log('📄 Page content sample:', pageContent.substring(0, 500));
            
            await page.screenshot({ path: 'oauth_redirect_failed.png' });
            console.log('📸 Screenshot saved: oauth_redirect_failed.png');
            
            return {
                timestamp: new Date().toISOString(),
                testResult: 'failed',
                oauthRedirectWorking: false,
                error: 'No redirect to Google OAuth occurred',
                currentUrl: currentUrl
            };
        }

    } catch (error) {
        console.error('💥 Test failed:', error.message);
        
        try {
            await page.screenshot({ path: 'oauth_test_error.png' });
            console.log('📸 Error screenshot saved: oauth_test_error.png');
        } catch (screenshotError) {
            // Ignore screenshot errors
        }
        
        return {
            timestamp: new Date().toISOString(),
            testResult: 'error',
            error: error.message
        };
        
    } finally {
        // Don't close browser immediately so user can see results
        console.log('\n⏳ Browser will close in 10 seconds...');
        await page.waitForTimeout(10000);
        await browser.close();
        console.log('🧹 Browser closed');
    }
}

// Run the test
testAuthenticatedOAuthFlow().then(result => {
    console.log('\n🏁 FINAL RESULTS:');
    console.log('═'.repeat(50));
    
    if (result.testResult === 'success') {
        if (result.googleConsentScreenAnalysis.containsBlackCoral) {
            console.log('🔴 CONCLUSION: Black Coral references found - OAuth app name needs updating');
            console.log('📋 ACTION REQUIRED: Update OAuth app name in Google Cloud Console');
            process.exit(1);
        } else {
            console.log('🟢 CONCLUSION: OAuth flow working correctly with new FYXERAI credentials');
            process.exit(0);
        }
    } else {
        console.log('🟡 CONCLUSION: OAuth flow test encountered issues');
        if (result.error) {
            console.log(`❌ Error: ${result.error}`);
        }
        process.exit(1);
    }
});