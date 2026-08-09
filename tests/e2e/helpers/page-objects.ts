/**
 * Page Object Models for inDoc E2E Tests
 * 
 * These classes provide a clean interface to interact with different pages
 * in the inDoc application.
 */

import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  readonly registerLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.getByLabel(/email|username/i);
    this.passwordInput = page.getByLabel(/password/i);
    this.loginButton = page.getByRole('button', { name: /login|sign in/i });
    this.registerLink = page.getByRole('link', { name: /register|sign up/i });
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
  }

  async expectToBeVisible() {
    await expect(this.page.getByRole('heading', { name: /login|sign in/i })).toBeVisible();
  }
}

export class DashboardPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly uploadButton: Locator;
  readonly documentsLink: Locator;
  readonly chatLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /dashboard/i });
    this.uploadButton = page.getByRole('button', { name: /upload/i });
    this.documentsLink = page.getByRole('link', { name: /documents/i });
    this.chatLink = page.getByRole('link', { name: /chat/i });
  }

  async goto() {
    await this.page.goto('/dashboard');
  }

  async expectToBeVisible() {
    await expect(this.heading).toBeVisible();
  }

  async navigateToUpload() {
    await this.uploadButton.click();
  }

  async navigateToDocuments() {
    await this.documentsLink.click();
  }

  async navigateToChat() {
    await this.chatLink.click();
  }
}

export class DocumentsPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly searchInput: Locator;
  readonly documentCards: Locator;
  readonly uploadButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /documents/i });
    this.searchInput = page.getByPlaceholder(/search/i);
    this.documentCards = page.locator('[data-testid="document-card"], .document-card, .MuiCard-root');
    this.uploadButton = page.getByRole('button', { name: /upload/i });
  }

  async goto() {
    await this.page.goto('/documents');
  }

  async expectToBeVisible() {
    await expect(this.heading).toBeVisible();
  }

  async search(query: string) {
    await this.searchInput.fill(query);
    await this.page.waitForTimeout(1500); // Wait for search results
  }

  async getDocumentCount(): Promise<number> {
    return await this.documentCards.count();
  }

  async clickFirstDocument() {
    await this.documentCards.first().click();
  }
}

export class UploadPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly fileInput: Locator;
  readonly titleInput: Locator;
  readonly descriptionInput: Locator;
  readonly uploadButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /upload/i });
    this.fileInput = page.locator('input[type="file"]');
    this.titleInput = page.getByLabel(/title/i);
    this.descriptionInput = page.getByLabel(/description/i);
    this.uploadButton = page.getByRole('button', { name: /upload|submit/i });
  }

  async goto() {
    await this.page.goto('/upload');
  }

  async expectToBeVisible() {
    await expect(this.heading).toBeVisible();
  }

  async uploadFile(filePath: string, title?: string, description?: string) {
    await this.fileInput.setInputFiles(filePath);
    
    if (title) {
      await this.titleInput.fill(title);
    }
    
    if (description) {
      await this.descriptionInput.fill(description);
    }
    
    await this.uploadButton.click();
  }
}

export class ChatPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly messageInput: Locator;
  readonly sendButton: Locator;
  readonly messages: Locator;
  readonly conversationList: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /chat/i });
    this.messageInput = page.getByPlaceholder(/message|ask|type/i);
    this.sendButton = page.getByRole('button', { name: /send/i });
    this.messages = page.locator('[data-testid="message"], .message');
    this.conversationList = page.locator('[data-testid="conversation"], .conversation-item');
  }

  async goto() {
    await this.page.goto('/chat');
  }

  async expectToBeVisible() {
    await expect(this.heading).toBeVisible();
  }

  async sendMessage(message: string) {
    await this.messageInput.fill(message);
    await this.sendButton.click();
    await this.page.waitForTimeout(2000); // Wait for response
  }

  async getMessageCount(): Promise<number> {
    return await this.messages.count();
  }

  async getConversationCount(): Promise<number> {
    return await this.conversationList.count();
  }
}

export class AuditPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly auditTable: Locator;
  readonly filterInput: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /audit/i });
    this.auditTable = page.locator('table, [data-testid="audit-table"]');
    this.filterInput = page.getByPlaceholder(/search|filter/i);
  }

  async goto() {
    await this.page.goto('/audit');
  }

  async expectToBeVisible() {
    await expect(this.heading).toBeVisible();
  }

  async filterByAction(action: string) {
    await this.filterInput.fill(action);
    await this.page.waitForTimeout(1000);
  }
}

export class UsersPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly usersTable: Locator;
  readonly addUserButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /users|user management/i });
    this.usersTable = page.locator('table, [data-testid="users-table"]');
    this.addUserButton = page.getByRole('button', { name: /add user/i });
  }

  async goto() {
    await this.page.goto('/users');
  }

  async expectToBeVisible() {
    await expect(this.heading).toBeVisible();
  }
}

export class TeamPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly teamMembersList: Locator;
  readonly addMemberButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /team/i });
    this.teamMembersList = page.locator('[data-testid="team-member"], .team-member');
    this.addMemberButton = page.getByRole('button', { name: /add member|invite/i });
  }

  async goto() {
    await this.page.goto('/team');
  }

  async expectToBeVisible() {
    await expect(this.heading).toBeVisible();
  }

  async getMemberCount(): Promise<number> {
    return await this.teamMembersList.count();
  }
}

export class SettingsPage {
  readonly page: Page;
  readonly heading: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /settings/i });
  }

  async goto() {
    await this.page.goto('/settings');
  }

  async expectToBeVisible() {
    await expect(this.heading).toBeVisible();
  }
}

/**
 * Navigation component that appears on all pages
 */
export class Navigation {
  readonly page: Page;
  readonly userMenuButton: Locator;
  readonly logoutButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.userMenuButton = page.getByRole('button', { name: /account|profile|user menu/i });
    this.logoutButton = page.getByRole('menuitem', { name: /logout|sign out/i });
  }

  async logout() {
    await this.userMenuButton.click();
    await this.logoutButton.click();
  }

  async navigateTo(pageName: string) {
    const link = this.page.getByRole('link', { name: new RegExp(pageName, 'i') });
    await link.click();
  }
}


