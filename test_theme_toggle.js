const puppeteer = require('puppeteer');

async function testThemeToggle() {
    console.log('Testing theme toggle in sidebar...\n');
    
    const browser = await puppeteer.launch({ 
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1280, height: 720 });
        
        console.log('Navigating to dashboard...');
        await page.goto('http://localhost:8002/', { waitUntil: 'networkidle2' });
        
        // Wait for page to load completely
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Check if theme toggle is present in sidebar
        const themeToggle = await page.$('aside button[data-theme-toggle]');
        console.log('Theme toggle found in sidebar:', !!themeToggle);
        
        if (themeToggle) {
            // Check if it's at the bottom of sidebar
            const sidebarHeight = await page.$eval('aside', el => el.getBoundingClientRect().height);
            const togglePosition = await page.$eval('aside button[data-theme-toggle]', el => {
                const rect = el.getBoundingClientRect();
                return {
                    top: rect.top,
                    bottom: rect.bottom,
                    height: rect.height
                };
            });
            
            console.log(`Sidebar height: ${sidebarHeight}px`);
            console.log(`Toggle position: top=${togglePosition.top}px, bottom=${togglePosition.bottom}px`);
            
            // Check if theme toggle is near the bottom (within 100px)
            const distanceFromBottom = sidebarHeight - (togglePosition.bottom - togglePosition.top);
            console.log(`Distance from bottom: ${distanceFromBottom}px`);
            console.log('Theme toggle positioned at bottom:', distanceFromBottom < 100);
            
            // Test theme toggle functionality
            console.log('\nTesting theme toggle click...');
            
            // Get initial theme state
            const initialTheme = await page.evaluate(() => {
                return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
            });
            console.log(`Initial theme: ${initialTheme}`);
            
            // Click theme toggle
            await themeToggle.click();
            await new Promise(resolve => setTimeout(resolve, 500)); // Wait for transition
            
            // Get theme state after click
            const newTheme = await page.evaluate(() => {
                return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
            });
            console.log(`Theme after click: ${newTheme}`);
            console.log('Theme toggle working:', initialTheme !== newTheme);
            
            // Check if button text changes
            const buttonText = await page.$eval('aside button[data-theme-toggle] span', el => el.textContent);
            console.log(`Button text: "${buttonText}"`);
            
            // Test click again to toggle back
            await themeToggle.click();
            await new Promise(resolve => setTimeout(resolve, 500));
            
            const finalTheme = await page.evaluate(() => {
                return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
            });
            console.log(`Theme after second click: ${finalTheme}`);
            console.log('Theme toggle works both ways:', finalTheme === initialTheme);
        }
        
        // Check if floating theme button is gone
        const floatingToggle = await page.$('button.fixed.top-4.right-4');
        console.log('Floating theme button removed:', !floatingToggle);
        
        // Check if login/signup is visible in header (no longer blocked)
        const headerSignIn = await page.$('header a[href*="login"]');
        const headerSignUp = await page.$('header a[href*="signup"]');
        
        console.log('\nHeader login/signup visibility:');
        console.log('Sign In visible:', !!headerSignIn);
        console.log('Sign Up visible:', !!headerSignUp);
        
        // Take final screenshot
        await page.screenshot({ path: 'theme_toggle_sidebar.png', fullPage: true });
        console.log('Screenshot saved as theme_toggle_sidebar.png');
        
    } catch (error) {
        console.error('Error during test:', error);
    } finally {
        await browser.close();
    }
}

testThemeToggle();