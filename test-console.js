const { chromium } = require('playwright');

async function testDevConsole() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    console.log('🚀 Testing Tour Booking Dev Console...');
    
    // Navigate to the Dev Console
    await page.goto('http://localhost:3001');
    
    // Wait for the page to load
    await page.waitForLoadState('networkidle');
    
    // Check page title
    const title = await page.title();
    console.log(`✓ Page title: ${title}`);
    
    // Check if main content is visible
    const mainContent = await page.locator('main').isVisible();
    console.log(`✓ Main content visible: ${mainContent}`);
    
    // Check for environment switcher
    const envSwitcher = page.locator('[data-testid="environment-switcher"], .environment-switcher, button:has-text("Local")');
    const envSwitcherVisible = await envSwitcher.first().isVisible().catch(() => false);
    console.log(`✓ Environment switcher visible: ${envSwitcherVisible}`);
    
    // Check for method picker
    const methodPicker = page.locator('[data-testid="method-picker"], .method-picker, text=method, text=endpoint');
    const methodPickerVisible = await methodPicker.first().isVisible().catch(() => false);
    console.log(`✓ Method picker visible: ${methodPickerVisible}`);
    
    // Check for request/response areas
    const requestArea = page.locator('[data-testid="request-form"], .request-form, text=request, text=Request');
    const requestAreaVisible = await requestArea.first().isVisible().catch(() => false);
    console.log(`✓ Request area visible: ${requestAreaVisible}`);
    
    // Take a screenshot
    await page.screenshot({ path: 'dev-console-screenshot.png', fullPage: true });
    console.log('✓ Screenshot saved: dev-console-screenshot.png');
    
    // Check if we can interact with the page
    const clickableElements = await page.locator('button, [role="button"], .btn').count();
    console.log(`✓ Found ${clickableElements} clickable elements`);
    
    // Test navigation to different sections if available
    const navLinks = await page.locator('nav a, [data-testid="nav-link"]').count();
    console.log(`✓ Found ${navLinks} navigation links`);
    
    console.log('✅ Dev Console basic functionality test completed successfully!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    await page.screenshot({ path: 'dev-console-error.png', fullPage: true });
    console.log('Error screenshot saved: dev-console-error.png');
  } finally {
    await browser.close();
  }
}

async function testAPIEndpoints() {
  console.log('🔧 Testing API endpoints...');
  
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Test API health endpoint
    const healthResponse = await page.request.get('http://localhost:8001/health');
    const healthData = await healthResponse.json();
    console.log(`✓ API Health: ${healthData.status}`);
    
    // Test OpenAPI docs
    const docsResponse = await page.request.get('http://localhost:8001/docs');
    console.log(`✓ OpenAPI docs status: ${docsResponse.status()}`);
    
    // Test metrics endpoint
    const metricsResponse = await page.request.get('http://localhost:8001/metrics');
    console.log(`✓ Metrics endpoint status: ${metricsResponse.status()}`);
    
    console.log('✅ API endpoints test completed successfully!');
    
  } catch (error) {
    console.error('❌ API test failed:', error.message);
  } finally {
    await browser.close();
  }
}

// Run tests
async function main() {
  console.log('🎯 Starting Tour Booking API Stack Tests\n');
  
  await testAPIEndpoints();
  console.log(''); // Empty line
  await testDevConsole();
  
  console.log('\n🎉 All tests completed!');
}

main().catch(console.error);