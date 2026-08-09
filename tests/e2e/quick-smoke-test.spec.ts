/**
 * Quick Smoke Test for inDoc
 * 
 * A faster test that validates critical paths only.
 * Run this for quick validation before full E2E suite.
 */

import { test, expect } from './fixtures';

test.describe('inDoc Smoke Test - Critical Paths', () => {
  test.setTimeout(60000); // 1 minute

  test('Critical Features Smoke Test', async ({ 
    page, 
    loginPage, 
    dashboardPage,
    documentsPage,
    chatPage,
  }) => {
    console.log('🔥 Running inDoc Smoke Test\n');

    // Test 1: Homepage loads
    await test.step('Homepage loads', async () => {
      await page.goto('/');
      // Wait a bit for React app to initialize and redirect
      await page.waitForTimeout(2000);
      await expect(page).toHaveURL(/\/(login|dashboard)/, { timeout: 10000 });
      console.log('✅ Homepage loads');
    });

    // Test 2: Login page accessible
    await test.step('Login page accessible', async () => {
      await loginPage.goto();
      await loginPage.expectToBeVisible();
      console.log('✅ Login page accessible');
    });

    // Test 3: Register page accessible
    await test.step('Register page accessible', async () => {
      await page.goto('/register');
      await expect(page.getByRole('heading', { name: /register/i })).toBeVisible();
      console.log('✅ Register page accessible');
    });

    // If you have a test account, you can add login and navigation tests
    // For now, just verify the pages load correctly

    console.log('\n✅ Smoke Test Passed - Critical paths working');
  });

  test('API Health Check', async ({ apiHelper }) => {
    await test.step('Backend API is healthy', async () => {
      const isHealthy = await apiHelper.checkHealth();
      expect(isHealthy).toBeTruthy();
      console.log('✅ Backend API is healthy');
    });
  });
});

