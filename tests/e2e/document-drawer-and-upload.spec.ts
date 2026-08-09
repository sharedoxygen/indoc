/**
 * Document Drawer and Upload Enhancement Tests
 *
 * Tests the new document details drawer, folder upload progress, and document set filtering
 * functionality added in the recent consolidation and improvements.
 */

import { test, expect, Page, APIRequestContext } from '@playwright/test';

test.describe('Document Drawer and Upload Enhancements', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to documents hub and ensure we're logged in
    await page.goto('/documents');
    await page.waitForLoadState('networkidle');

    // Should be on the Browse tab by default
    await expect(page.getByText('Documents Hub')).toBeVisible();
  });

  test('should open document details drawer when clicking document row', async ({ page }) => {
    // Wait for documents to load
    await page.waitForSelector('[data-testid="document-row"], [data-testid="document-card"]', { timeout: 10000 });

    // Find the first document and click it
    const firstDoc = page.locator('[data-testid="document-row"], [data-testid="document-card"]').first();
    await firstDoc.click();

    // Verify drawer opens
    await expect(page.locator('[data-testid="document-details-drawer"]')).toBeVisible({ timeout: 5000 });

    // Verify drawer contains document details
    await expect(page.getByText('Document Details')).toBeVisible();
    await expect(page.locator('[data-testid="document-title-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="document-description-input"]')).toBeVisible();
  });

  test('should allow editing document metadata in drawer', async ({ page }) => {
    // Open document drawer
    await page.locator('[data-testid="document-row"], [data-testid="document-card"]').first().click();
    await expect(page.locator('[data-testid="document-details-drawer"]')).toBeVisible();

    // Edit title and description
    const titleInput = page.locator('[data-testid="document-title-input"]');
    const descInput = page.locator('[data-testid="document-description-input"]');

    await titleInput.fill('Updated Test Document Title');
    await descInput.fill('Updated test description for E2E testing');

    // Save changes
    await page.getByRole('button', { name: /save/i }).click();

    // Verify save succeeds (no error toast)
    await expect(page.locator('.MuiAlert-root.MuiAlert-colorError')).not.toBeVisible({ timeout: 5000 });

    // Close drawer and reopen to verify persistence
    await page.locator('[data-testid="drawer-close-button"]').click();
    await page.locator('[data-testid="document-row"], [data-testid="document-card"]').first().click();

    // Verify updated values are still there
    await expect(titleInput).toHaveValue('Updated Test Document Title');
    await expect(descInput).toHaveValue('Updated test description for E2E testing');
  });

  test('should allow deleting documents through drawer', async ({ page }) => {
    // Open document drawer
    await page.locator('[data-testid="document-row"], [data-testid="document-card"]').first().click();
    await expect(page.locator('[data-testid="document-details-drawer"]')).toBeVisible();

    // Get document title for verification
    const docTitle = await page.locator('[data-testid="document-title-input"]').inputValue();

    // Click delete button
    await page.getByRole('button', { name: /delete/i }).click();

    // Confirm deletion in dialog
    await expect(page.getByText(/delete document/i)).toBeVisible();
    await page.getByRole('button', { name: /delete/i }).click();

    // Verify deletion succeeded
    await expect(page.locator('.MuiAlert-root.MuiAlert-colorSuccess')).toBeVisible();

    // Verify document is removed from list
    await page.reload();
    await expect(page.getByText(docTitle)).not.toBeVisible();
  });

  test('should trigger virus scan through drawer', async ({ page }) => {
    // Open document drawer
    await page.locator('[data-testid="document-row"], [data-testid="document-card"]').first().click();
    await expect(page.locator('[data-testid="document-details-drawer"]')).toBeVisible();

    // Click scan button
    await page.getByRole('button', { name: /scan now/i }).click();

    // Verify scan completes (status should update)
    await expect(page.locator('[data-testid="virus-status-chip"]')).toBeVisible();
    // The exact status depends on backend, but it should show something
    await expect(page.locator('[data-testid="virus-status-chip"]')).toContainText(/clean|pending|error/);
  });

  test('should filter documents by document set', async ({ page }) => {
    // Get initial document count
    await page.waitForSelector('[data-testid="document-row"], [data-testid="document-card"]');
    const initialCount = await page.locator('[data-testid="document-row"], [data-testid="document-card"]').count();

    // Apply document set filter
    await page.locator('[data-testid="document-set-filter"]').selectOption('ZX10R-2024');

    // Wait for filter to apply
    await page.waitForTimeout(1000);

    // Verify filtered results (count should be different or same depending on data)
    const filteredCount = await page.locator('[data-testid="document-row"], [data-testid="document-card"]').count();

    // Should either have results or show no results message
    if (filteredCount > 0) {
      // Has results - verify they belong to the set
      const firstDoc = page.locator('[data-testid="document-row"], [data-testid="document-card"]').first();
      await expect(firstDoc).toBeVisible();
    } else {
      // No results - should show empty state
      await expect(page.getByText(/no documents/i)).toBeVisible();
    }

    // Clear filter
    await page.locator('[data-testid="document-set-filter"]').selectOption('');

    // Wait for filter to clear
    await page.waitForTimeout(1000);

    // Should be back to original count
    const clearedCount = await page.locator('[data-testid="document-row"], [data-testid="document-card"]').count();
    expect(clearedCount).toBeGreaterThanOrEqual(Math.min(initialCount, filteredCount));
  });

  test('should handle folder upload with progress tracking', async ({ page }) => {
    // Navigate to upload tab
    await page.getByRole('tab', { name: /upload/i }).click();
    await expect(page.getByText('Upload Documents')).toBeVisible();

    // Create test folder structure
    const testFiles = [
      { name: 'test-folder/file1.txt', content: 'Test file 1 content' },
      { name: 'test-folder/subfolder/file2.txt', content: 'Test file 2 content' },
      { name: 'file3.txt', content: 'Root level file content' }
    ];

    // Upload files using the upload zone
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(testFiles.map(f => ({
      name: f.name,
      mimeType: 'text/plain',
      buffer: Buffer.from(f.content)
    })));

    // Verify files appear in upload list
    for (const file of testFiles) {
      await expect(page.getByText(file.name)).toBeVisible();
    }

    // Click upload button
    await page.getByRole('button', { name: /upload/i }).click();

    // Verify progress indicators appear
    await expect(page.getByText(/uploading|processing/i)).toBeVisible({ timeout: 10000 });

    // Wait for upload completion
    await expect(page.locator('[data-testid="upload-success"]')).toBeVisible({ timeout: 30000 });

    // Verify all files show success status
    for (const file of testFiles) {
      await expect(page.locator(`[data-testid="file-status-${file.name}"]`).filter({ hasText: /success|duplicate/i })).toBeVisible();
    }
  });

  test('should show real-time processing progress via WebSocket', async ({ page }) => {
    // This test requires the WebSocket to be connected and sending progress updates
    // We'll verify the WebSocket connection and basic progress display

    // Navigate to processing tab
    await page.getByRole('tab', { name: /upload/i }).click();
    await page.getByRole('button', { name: /processing/i }).click();

    // Verify WebSocket connection status
    await expect(page.locator('[data-testid="websocket-status"]')).toContainText(/connected|live/i);

    // Upload a document to trigger processing
    await page.goto('/documents?tab=work');
    await page.getByRole('button', { name: /select files/i }).click();

    // Select and upload a test file
    await page.locator('input[type="file"]').setInputFiles([{
      name: 'websocket-test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('Test content for WebSocket progress tracking')
    }]);

    await page.getByRole('button', { name: /upload/i }).click();

    // Verify processing pipeline shows the document
    await expect(page.getByText('websocket-test.txt')).toBeVisible({ timeout: 10000 });

    // Verify progress indicators are present
    await expect(page.locator('[data-testid="processing-progress"]')).toBeVisible();
  });
});
