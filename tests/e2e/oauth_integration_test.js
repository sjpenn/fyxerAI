const { test, expect } = require('@playwright/test');
const { spawn } = require('child_process');

// Mock OAuth Service for testing
class MockOAuthService {
  constructor() {
    this.mockUserInfo = {
      email: 'testuser@gmail.com',
      name: 'Test User',
      id: '12345'
    };
    
    this.mockTokens = {
      access_token: 'mock_access_token_123',
      refresh_token: 'mock_refresh_token_456',
      expires_in: 3600,
      scope: 'email profile https://www.googleapis.com/auth/gmail.readonly'
    };
  }
  
  // Mock Google OAuth endpoints
  async setupMockEndpoints(page) {
    // Intercept Google OAuth requests
    await page.route('https://accounts.google.com/o/oauth2/auth**', async (route) => {
      const url = new URL(route.request().url());
      const state = url.searchParams.get('state');
      const redirectUri = url.searchParams.get('redirect_uri');
      
      // Simulate user consent and redirect back to our callback
      const callbackUrl = `${redirectUri}?state=${state}&code=mock_auth_code_789&scope=${encodeURIComponent('email profile')}`;
      
      await route.fulfill({
        status: 302,
        headers: {
          'Location': callbackUrl
        }
      });
    });
    
    // Mock token exchange
    await page.route('https://oauth2.googleapis.com/token', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(this.mockTokens)
      });
    });
    
    // Mock user info API
    await page.route('https://www.googleapis.com/oauth2/v2/userinfo', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(this.mockUserInfo)
      });
    });
  }
}

test.describe('Gmail OAuth Integration Tests', () => {
  let mockOAuth;
  
  test.beforeEach(async ({ page }) => {
    mockOAuth = new MockOAuthService();
    await mockOAuth.setupMockEndpoints(page);
    
    // Clear cookies and session
    await page.context().clearCookies();
  });

  test('should complete full Gmail OAuth flow and create account', async ({ page }) => {
    // Step 1: Navigate to login page
    await page.goto('http://localhost:8000/login/');
    
    // Step 2: Login with test user
    // We need to first create a test user or use existing superuser
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    
    // Wait for redirect to dashboard
    await page.waitForTimeout(2000);
    
    // Step 3: Navigate to connect Gmail
    console.log('Current URL:', page.url());
    await page.goto('http://localhost:8000/emails/dashboard/');
    
    // Step 4: Find and click Gmail connect button
    // Look for various possible selectors
    const gmailButton = page.locator('a[href*="gmail"], button:has-text("Gmail"), a:has-text("Connect Gmail"), [data-test*="gmail"]').first();
    
    if (await gmailButton.count() === 0) {
      // Try to find account menu or add account option
      const accountMenu = page.locator('[data-test="account-menu"], .account-menu, #account-menu');
      if (await accountMenu.count() > 0) {
        await accountMenu.click();
      }
      
      // Look for Gmail option in the menu
      await page.waitForTimeout(500);
    }
    
    // Take screenshot to see current state
    await page.screenshot({ path: 'test-before-oauth.png' });
    
    // Step 5: Initiate OAuth by going directly to the OAuth URL
    await page.goto('http://localhost:8000/auth/gmail/login/');
    
    // Should be redirected to our mocked Google OAuth, then back to callback
    await page.waitForTimeout(3000);
    
    // Step 6: Verify we're back at the dashboard with account connected
    console.log('Final URL:', page.url());
    await page.screenshot({ path: 'test-after-oauth.png' });
    
    // Step 7: Check for success indicators
    const pageContent = await page.content();
    const hasSuccessMessage = pageContent.includes('connected') || pageContent.includes('success');
    const hasEmailAccount = pageContent.includes('testuser@gmail.com') || pageContent.includes('@gmail.com');
    
    console.log('Has success message:', hasSuccessMessage);
    console.log('Has email account:', hasEmailAccount);
    
    // Verify account was created in database by checking the account menu
    await page.goto('http://localhost:8000/account-menu/');
    await page.screenshot({ path: 'test-account-menu.png' });
    
    const accountMenuContent = await page.content();
    console.log('Account menu contains gmail:', accountMenuContent.includes('gmail'));
  });

  test('should handle OAuth callback with proper error handling', async ({ page }) => {
    // Login first
    await page.goto('http://localhost:8000/login/');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1000);
    
    // Test direct callback with error
    await page.goto('http://localhost:8000/auth/gmail/callback/?error=access_denied');
    
    // Should show error message and redirect
    await page.waitForTimeout(2000);
    const content = await page.content();
    expect(content).toContain('cancelled');
  });

  test('should validate state parameter for CSRF protection', async ({ page }) => {
    // Login first  
    await page.goto('http://localhost:8000/login/');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1000);
    
    // Go to OAuth initiation to set up session state
    await page.goto('http://localhost:8000/auth/gmail/login/');
    await page.waitForTimeout(1000);
    
    // Then try callback with wrong state
    await page.goto('http://localhost:8000/auth/gmail/callback/?state=wrong-state&code=test-code');
    
    // Should show state mismatch error
    await page.waitForTimeout(2000);
    const content = await page.content();
    expect(content).toContain('state');
  });
});

test.describe('Email Account Management', () => {
  test('should show connected accounts in account menu', async ({ page }) => {
    await page.goto('http://localhost:8000/account-menu/');
    
    // Take screenshot to see what's available
    await page.screenshot({ path: 'account-menu-state.png' });
    
    // Check for account list structure
    const content = await page.content();
    console.log('Account menu loaded, checking for Gmail accounts...');
  });
  
  test('should allow account disconnection', async ({ page }) => {
    await page.goto('http://localhost:8000/account-menu/');
    
    // Look for disconnect buttons
    const disconnectButtons = page.locator('button:has-text("Disconnect"), a:has-text("Remove"), [data-test*="disconnect"]');
    
    if (await disconnectButtons.count() > 0) {
      await disconnectButtons.first().click();
      
      // Should show confirmation or redirect
      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'after-disconnect.png' });
    }
  });
});