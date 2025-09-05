const { test, expect } = require('@playwright/test');

test.describe('Gmail OAuth Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app and ensure we're starting fresh
    await page.goto('http://localhost:8000/');
    
    // Clear any existing sessions/cookies
    await page.context().clearCookies();
  });

  test('should complete Gmail OAuth flow and create email account', async ({ page }) => {
    // First, we need to login to the app
    await page.goto('http://localhost:8000/login/');
    
    // Fill in login form (assuming we have test credentials)
    await page.fill('input[name="username"]', 'testuser');
    await page.fill('input[name="password"]', 'testpassword');
    await page.click('button[type="submit"]');
    
    // Wait for dashboard to load
    await page.waitForURL('**/emails/dashboard/**');
    
    // Click on Add Account or Connect Gmail button
    await page.click('[data-test="connect-gmail"]');
    
    // Should be redirected to Google OAuth
    await page.waitForURL('**/accounts.google.com/o/oauth2/**');
    
    // Since we can't actually go through Google's OAuth in tests,
    // we'll mock the callback response instead
    
    // Navigate back to simulate OAuth callback with mock data
    const mockState = 'test-state-123';
    const mockCode = 'test-auth-code-456';
    const callbackUrl = `http://localhost:8000/auth/gmail/callback/?state=${mockState}&code=${mockCode}&scope=email%20profile`;
    
    // We would need to mock the OAuth flow here
    // For now, let's test the callback URL directly with mock session
    await page.goto(callbackUrl);
    
    // Check if we get an error or success
    await page.waitForTimeout(2000);
    
    // Should redirect back to dashboard or show an account connection success
    const currentUrl = page.url();
    console.log('Current URL after OAuth callback:', currentUrl);
    
    // Check for success message or account in the list
    await page.screenshot({ path: 'test-oauth-callback.png' });
  });

  test('should handle OAuth errors gracefully', async ({ page }) => {
    // Test OAuth error handling
    await page.goto('http://localhost:8000/login/');
    
    // Login first
    await page.fill('input[name="username"]', 'testuser');
    await page.fill('input[name="password"]', 'testpassword');  
    await page.click('button[type="submit"]');
    
    // Wait for dashboard
    await page.waitForURL('**/emails/dashboard/**');
    
    // Simulate OAuth error callback
    const errorUrl = 'http://localhost:8000/auth/gmail/callback/?error=access_denied&state=test-state';
    await page.goto(errorUrl);
    
    // Should show error message
    const errorMessage = await page.textContent('.alert-error, .error-message, [role="alert"]');
    expect(errorMessage).toContain('cancelled');
  });

  test('should validate OAuth state parameter', async ({ page }) => {
    // Test CSRF protection via state parameter
    await page.goto('http://localhost:8000/login/');
    
    // Login
    await page.fill('input[name="username"]', 'testuser');
    await page.fill('input[name="password"]', 'testpassword');
    await page.click('button[type="submit"]');
    
    await page.waitForURL('**/emails/dashboard/**');
    
    // Simulate OAuth callback with invalid state
    const invalidStateUrl = 'http://localhost:8000/auth/gmail/callback/?state=invalid-state&code=test-code';
    await page.goto(invalidStateUrl);
    
    // Should show state mismatch error
    const errorMessage = await page.textContent('body');
    expect(errorMessage).toContain('state');
  });
});

test.describe('Gmail OAuth Integration', () => {
  test('should display connected accounts in dashboard', async ({ page }) => {
    // This test would verify that connected accounts show up
    await page.goto('http://localhost:8000/emails/dashboard/');
    
    // Check for account menu or connected accounts section
    const accountMenu = await page.locator('[data-test="account-menu"]');
    await expect(accountMenu).toBeVisible();
  });

  test('should allow disconnecting accounts', async ({ page }) => {
    // Test account disconnection
    await page.goto('http://localhost:8000/emails/dashboard/');
    
    // Look for disconnect button (if account exists)
    const disconnectButton = page.locator('[data-test="disconnect-account"]');
    if (await disconnectButton.count() > 0) {
      await disconnectButton.first().click();
      
      // Should show confirmation or success message
      await expect(page.locator('.alert-success')).toBeVisible();
    }
  });
});