/**
 * Playwright Test Fixtures for inDoc
 * 
 * Custom fixtures provide reusable test setup and teardown logic.
 */

import { test as base, expect } from '@playwright/test';
import { APIHelper } from './helpers/api-helpers';
import {
  LoginPage,
  DashboardPage,
  DocumentsPage,
  UploadPage,
  ChatPage,
  AuditPage,
  UsersPage,
  TeamPage,
  SettingsPage,
  Navigation,
} from './helpers/page-objects';

interface PageObjects {
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
  documentsPage: DocumentsPage;
  uploadPage: UploadPage;
  chatPage: ChatPage;
  auditPage: AuditPage;
  usersPage: UsersPage;
  teamPage: TeamPage;
  settingsPage: SettingsPage;
  navigation: Navigation;
}

interface APIHelpers {
  apiHelper: APIHelper;
}

// Extend base test with page objects
export const test = base.extend<PageObjects & APIHelpers>({
  // Page Objects
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },

  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },

  documentsPage: async ({ page }, use) => {
    await use(new DocumentsPage(page));
  },

  uploadPage: async ({ page }, use) => {
    await use(new UploadPage(page));
  },

  chatPage: async ({ page }, use) => {
    await use(new ChatPage(page));
  },

  auditPage: async ({ page }, use) => {
    await use(new AuditPage(page));
  },

  usersPage: async ({ page }, use) => {
    await use(new UsersPage(page));
  },

  teamPage: async ({ page }, use) => {
    await use(new TeamPage(page));
  },

  settingsPage: async ({ page }, use) => {
    await use(new SettingsPage(page));
  },

  navigation: async ({ page }, use) => {
    await use(new Navigation(page));
  },

  // API Helper
  apiHelper: async ({ request }, use) => {
    const baseURL = process.env.E2E_API_URL || 'http://localhost:8000';
    const helper = new APIHelper(request, baseURL);
    await use(helper);
  },
});

export { expect };


