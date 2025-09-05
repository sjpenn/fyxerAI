const puppeteer = require('puppeteer');

async function testNavbar() {
    const browser = await puppeteer.launch({ 
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1280, height: 720 });
        
        console.log('Navigating to dashboard...');
        await page.goto('http://localhost:8002/', { waitUntil: 'networkidle2' });
        
        // Take a screenshot
        await page.screenshot({ path: 'dashboard_before.png', fullPage: true });
        console.log('Screenshot saved as dashboard_before.png');
        
        // Check for authentication elements in header
        console.log('\n=== HEADER ANALYSIS ===');
        const headerExists = await page.$('header');
        console.log('Header element exists:', !!headerExists);
        
        if (headerExists) {
            const headerText = await page.$eval('header', el => el.textContent);
            console.log('Header text content:', headerText.trim());
            
            // Check for sign in/sign up links
            const signInLink = await page.$('header a[href*="login"]');
            const signUpLink = await page.$('header a[href*="signup"]');
            
            console.log('Sign In link in header:', !!signInLink);
            console.log('Sign Up link in header:', !!signUpLink);
            
            // Check connection status
            const connectionStatus = await page.$eval('header', el => {
                const statusElement = el.querySelector('[x-text*="Connected"]');
                return statusElement ? statusElement.textContent : 'Not found';
            }).catch(() => 'Not found');
            console.log('Connection status:', connectionStatus);
        }
        
        // Check sidebar
        console.log('\n=== SIDEBAR ANALYSIS ===');
        const sidebar = await page.$('aside');
        console.log('Sidebar exists:', !!sidebar);
        
        if (sidebar) {
            const sidebarText = await page.$eval('aside', el => el.textContent);
            console.log('Sidebar contains "Get Started":', sidebarText.includes('Get Started'));
            console.log('Sidebar contains "Sign In":', sidebarText.includes('Sign In'));
            console.log('Sidebar contains "Sign Up":', sidebarText.includes('Sign Up'));
            
            // Check debug comment
            const debugComment = await page.evaluate(() => {
                const walker = document.createTreeWalker(
                    document.querySelector('aside'),
                    NodeFilter.SHOW_COMMENT,
                    null,
                    false
                );
                
                let comment;
                while (comment = walker.nextNode()) {
                    if (comment.nodeValue.includes('Debug: User auth status')) {
                        return comment.nodeValue;
                    }
                }
                return null;
            });
            console.log('Debug comment:', debugComment);
        }
        
        // Check main content area
        console.log('\n=== MAIN CONTENT ANALYSIS ===');
        const mainContent = await page.$('#main-content, main');
        if (mainContent) {
            const mainText = await page.$eval('#main-content, main', el => el.textContent);
            console.log('Main content contains "Authentication Required":', mainText.includes('Authentication Required'));
            console.log('Main content contains "Sign In":', mainText.includes('Sign In'));
        }
        
        // Wait a moment for HTMX to load
        await page.waitForTimeout(2000);
        
        // Take another screenshot after HTMX loads
        await page.screenshot({ path: 'dashboard_after_htmx.png', fullPage: true });
        console.log('Screenshot after HTMX loading saved as dashboard_after_htmx.png');
        
        console.log('\n=== TEST COMPLETE ===');
        
    } catch (error) {
        console.error('Error during test:', error);
    } finally {
        await browser.close();
    }
}

testNavbar();