#!/usr/bin/env node

/**
 * Puppeteer test to validate OAuth flow with new FYXERAI credentials
 * Tests both the debug page and actual login flow
 */

const puppeteer = require('puppeteer');
const path = require('path');

class OAuthValidator {
    constructor() {
        this.browser = null;
        this.page = null;
        this.baseUrl = process.env.BASE_URL || 'http://localhost:8000';
    }

    async init() {
        console.log('🚀 Initializing Puppeteer for OAuth validation...');
        this.browser = await puppeteer.launch({
            headless: false, // Show browser for debugging
            slowMo: 100, // Slow down actions for visibility
            args: [
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        });
        this.page = await this.browser.newPage();
        
        // Set viewport
        await this.page.setViewport({ width: 1366, height: 768 });
        
        // Set user agent
        await this.page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
    }

    async validateDebugPage() {
        console.log('\n📊 Testing OAuth Debug Page...');
        
        try {
            await this.page.goto(`${this.baseUrl}/auth/debug/`, {
                waitUntil: 'networkidle2',
                timeout: 10000
            });

            // Check page title
            const title = await this.page.title();
            console.log(`✅ Page loaded: ${title}`);

            // Check for Black Coral references
            const bodyText = await this.page.evaluate(() => document.body.textContent);
            if (bodyText.includes('Black Coral')) {
                console.log('⚠️  WARNING: "Black Coral" references still found on debug page');
                console.log('   This suggests the OAuth app name hasn\'t been updated');
            } else {
                console.log('✅ No "Black Coral" references found');
            }

            // Check configuration status
            const configStatus = await this.page.evaluate(() => {
                const rows = document.querySelectorAll('.flex.justify-between');
                const status = {};
                
                rows.forEach(row => {
                    const label = row.querySelector('.text-slate-600')?.textContent?.trim();
                    const value = row.querySelector('.font-mono')?.textContent?.trim();
                    if (label && value) {
                        status[label.replace(':', '')] = value;
                    }
                });
                
                return status;
            });

            console.log('\n📋 Configuration Status:');
            Object.entries(configStatus).forEach(([key, value]) => {
                const status = value.includes('✅') ? '✅' : '❌';
                console.log(`   ${status} ${key}: ${value}`);
            });

            // Check if OAuth test button is available
            const testButton = await this.page.$('a[href*="gmail_oauth_login"]');
            if (testButton) {
                console.log('✅ OAuth test button found and ready');
                return true;
            } else {
                console.log('❌ OAuth test button not available (missing credentials)');
                return false;
            }

        } catch (error) {
            console.error('❌ Debug page validation failed:', error.message);
            return false;
        }
    }

    async testOAuthFlow() {
        console.log('\n🔐 Testing OAuth Login Flow...');
        
        try {
            // Navigate to login page
            await this.page.goto(`${this.baseUrl}/auth/debug/`, {
                waitUntil: 'networkidle2'
            });

            // Click the Gmail OAuth test button
            const testButton = await this.page.$('a[href*="gmail_oauth_login"]');
            if (!testButton) {
                console.log('❌ OAuth test button not found - credentials not configured');
                return false;
            }

            console.log('🔗 Clicking Gmail OAuth test button...');
            await testButton.click();

            // Wait for navigation to Google
            await this.page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 10000 });

            const currentUrl = this.page.url();
            console.log(`📍 Current URL: ${currentUrl}`);

            // Check if we're on Google's OAuth page
            if (currentUrl.includes('accounts.google.com')) {
                console.log('✅ Successfully redirected to Google OAuth');
                
                // Check for project/app name in the OAuth consent screen
                await this.page.waitForSelector('h1, [data-test-id="app-name"]', { timeout: 5000 });
                
                const appNameElements = await this.page.$$eval('*', (elements) => {
                    return elements
                        .filter(el => el.textContent && (
                            el.textContent.includes('Black Coral') || 
                            el.textContent.includes('FYXERAI') ||
                            el.textContent.includes('fyxer')
                        ))
                        .map(el => el.textContent.trim());
                });

                if (appNameElements.some(text => text.includes('Black Coral'))) {
                    console.log('⚠️  WARNING: Google OAuth still shows "Black Coral" app name');
                    console.log('   You need to update the OAuth app name in Google Cloud Console');
                    
                    // Take screenshot for evidence
                    await this.page.screenshot({ path: 'oauth_black_coral_evidence.png', fullPage: true });
                    console.log('📸 Screenshot saved: oauth_black_coral_evidence.png');
                    
                    return { success: false, issue: 'oauth_app_name' };
                } else if (appNameElements.some(text => text.toLowerCase().includes('fyxer'))) {
                    console.log('✅ Google OAuth shows FYXERAI app name');
                    return { success: true, issue: null };
                } else {
                    console.log('⚠️  Unable to determine OAuth app name from consent screen');
                    console.log('   App name elements found:', appNameElements);
                    
                    // Take screenshot for manual review
                    await this.page.screenshot({ path: 'oauth_consent_screen.png', fullPage: true });
                    console.log('📸 Screenshot saved for manual review: oauth_consent_screen.png');
                    
                    return { success: false, issue: 'indeterminate' };
                }

            } else if (currentUrl.includes('error')) {
                console.log('❌ OAuth error detected in URL');
                
                // Try to extract error details
                const errorParams = new URLSearchParams(currentUrl.split('?')[1] || '');
                console.log('   Error:', errorParams.get('error'));
                console.log('   Description:', errorParams.get('error_description'));
                
                return { success: false, issue: 'oauth_error' };
            } else {
                console.log('❌ Unexpected redirect destination');
                console.log(`   Expected Google OAuth, got: ${currentUrl}`);
                return { success: false, issue: 'redirect_error' };
            }

        } catch (error) {
            console.error('❌ OAuth flow test failed:', error.message);
            return { success: false, issue: 'test_error' };
        }
    }

    async generateReport() {
        console.log('\n📄 Generating OAuth Validation Report...');
        
        const debugPageValid = await this.validateDebugPage();
        let oauthFlowResult = { success: false, issue: 'not_tested' };
        
        if (debugPageValid) {
            oauthFlowResult = await this.testOAuthFlow();
        }

        const report = {
            timestamp: new Date().toISOString(),
            baseUrl: this.baseUrl,
            debugPage: {
                accessible: debugPageValid,
                credentialsConfigured: debugPageValid
            },
            oauthFlow: oauthFlowResult,
            recommendations: []
        };

        // Generate recommendations
        if (!debugPageValid) {
            report.recommendations.push('Configure Google OAuth credentials in your .env file');
            report.recommendations.push('Ensure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set');
        }

        if (oauthFlowResult.issue === 'oauth_app_name') {
            report.recommendations.push('Update OAuth app name in Google Cloud Console from "Black Coral" to "FYXERAI"');
            report.recommendations.push('Go to https://console.cloud.google.com/apis/credentials and edit your OAuth 2.0 Client ID');
        }

        if (oauthFlowResult.issue === 'oauth_error') {
            report.recommendations.push('Check that your redirect URI is correctly configured in Google Cloud Console');
            report.recommendations.push(`Ensure this URL is in authorized redirect URIs: ${this.baseUrl}/auth/google/callback/`);
        }

        // Save report
        const reportPath = path.join(__dirname, 'oauth_validation_report.json');
        require('fs').writeFileSync(reportPath, JSON.stringify(report, null, 2));
        console.log(`📄 Report saved: ${reportPath}`);

        return report;
    }

    async cleanup() {
        if (this.browser) {
            await this.browser.close();
            console.log('🧹 Browser closed');
        }
    }

    async run() {
        try {
            await this.init();
            const report = await this.generateReport();
            
            console.log('\n🎯 VALIDATION SUMMARY:');
            console.log('='.repeat(50));
            
            if (report.oauthFlow.success) {
                console.log('✅ OAuth flow is working correctly with FYXERAI credentials');
            } else {
                console.log('❌ OAuth flow has issues that need to be resolved');
                console.log('\n📋 Recommended Actions:');
                report.recommendations.forEach((rec, i) => {
                    console.log(`   ${i + 1}. ${rec}`);
                });
            }
            
            return report;
            
        } catch (error) {
            console.error('💥 Validation failed:', error);
            return null;
        } finally {
            await this.cleanup();
        }
    }
}

// Run the validator
if (require.main === module) {
    const validator = new OAuthValidator();
    validator.run().then(result => {
        process.exit(result?.oauthFlow.success ? 0 : 1);
    });
}

module.exports = OAuthValidator;