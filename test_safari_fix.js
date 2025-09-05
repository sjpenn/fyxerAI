const puppeteer = require('puppeteer');

async function testBothBrowsers() {
    console.log('Testing login/signup visibility in both Chromium and WebKit...\n');
    
    // Test in Chromium (Chrome/Edge)
    console.log('=== CHROMIUM TEST ===');
    await testBrowser('chromium');
    
    // Test in WebKit (Safari)
    console.log('\n=== WEBKIT (Safari) TEST ===');
    await testBrowser('webkit');
}

async function testBrowser(engine) {
    let browser;
    try {
        // Launch browser based on engine
        if (engine === 'webkit') {
            browser = await puppeteer.launch({ 
                product: 'webkit',
                headless: false,
                args: ['--no-sandbox', '--disable-setuid-sandbox']
            });
        } else {
            browser = await puppeteer.launch({ 
                headless: false,
                args: ['--no-sandbox', '--disable-setuid-sandbox']
            });
        }
        
        const page = await browser.newPage();
        await page.setViewport({ width: 1280, height: 720 });
        
        console.log(`Navigating to dashboard in ${engine}...`);
        await page.goto('http://localhost:8002/', { waitUntil: 'networkidle2' });
        
        // Take a screenshot
        await page.screenshot({ path: `dashboard_${engine}_fixed.png`, fullPage: true });
        console.log(`Screenshot saved as dashboard_${engine}_fixed.png`);
        
        // Wait for page to fully render
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Check header authentication elements
        const headerSignIn = await page.$('header a[href*="login"]');
        const headerSignUp = await page.$('header a[href*="signup"]');
        
        console.log(`Header Sign In visible: ${!!headerSignIn}`);
        console.log(`Header Sign Up visible: ${!!headerSignUp}`);
        
        if (headerSignIn) {
            const signInText = await page.evaluate(el => el.textContent, headerSignIn);
            const signInVisible = await page.evaluate(el => {
                const styles = window.getComputedStyle(el);
                return styles.display !== 'none' && styles.visibility !== 'hidden' && styles.opacity !== '0';
            }, headerSignIn);
            console.log(`Header Sign In text: "${signInText.trim()}", visible: ${signInVisible}`);
        }
        
        if (headerSignUp) {
            const signUpText = await page.evaluate(el => el.textContent, headerSignUp);
            const signUpVisible = await page.evaluate(el => {
                const styles = window.getComputedStyle(el);
                return styles.display !== 'none' && styles.visibility !== 'hidden' && styles.opacity !== '0';
            }, headerSignUp);
            const signUpBg = await page.evaluate(el => {
                const styles = window.getComputedStyle(el);
                return styles.background || styles.backgroundColor;
            }, headerSignUp);
            console.log(`Header Sign Up text: "${signUpText.trim()}", visible: ${signUpVisible}`);
            console.log(`Header Sign Up background: "${signUpBg}"`);
        }
        
        // Check sidebar authentication elements
        const sidebarSignIn = await page.$('aside a[href*="login"]');
        const sidebarSignUp = await page.$('aside a[href*="signup"]');
        
        console.log(`Sidebar Sign In visible: ${!!sidebarSignIn}`);
        console.log(`Sidebar Sign Up visible: ${!!sidebarSignUp}`);
        
        // Check if Alpine.js is working
        const alpineWorking = await page.evaluate(() => {
            return typeof window.Alpine !== 'undefined';
        });
        console.log(`Alpine.js loaded: ${alpineWorking}`);
        
        // Check console errors
        const logs = [];
        page.on('console', msg => {
            if (msg.type() === 'error') {
                logs.push(`Console error: ${msg.text()}`);
            }
        });
        
        // Wait a bit more to catch any errors
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        if (logs.length > 0) {
            console.log('Console errors found:');
            logs.forEach(log => console.log(`  ${log}`));
        } else {
            console.log('No console errors detected');
        }
        
        console.log(`${engine} test completed successfully!\n`);
        
    } catch (error) {
        console.error(`Error testing ${engine}:`, error);
    } finally {
        if (browser) {
            await browser.close();
        }
    }
}

testBothBrowsers().catch(console.error);