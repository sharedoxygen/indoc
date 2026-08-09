/**
 * API Helper Functions for E2E Tests
 * 
 * These helpers interact directly with the backend API for setup/teardown
 * and verification purposes.
 */

import { APIRequestContext } from '@playwright/test';

export interface TestUser {
  email: string;
  password: string;
  role: string;
  fullName: string;
  id?: number;
  token?: string;
}

export class APIHelper {
  constructor(private request: APIRequestContext, private baseURL: string) {}

  /**
   * Create a user via API (faster than UI registration)
   */
  async createUser(user: TestUser): Promise<TestUser> {
    const response = await this.request.post(`${this.baseURL}/api/v1/auth/register`, {
      data: {
        email: user.email,
        password: user.password,
        full_name: user.fullName,
        role: user.role,
      },
    });

    if (response.ok()) {
      const data = await response.json();
      return { ...user, id: data.id };
    }

    throw new Error(`Failed to create user: ${response.status()}`);
  }

  /**
   * Login and get access token
   */
  async login(email: string, password: string): Promise<string> {
    const response = await this.request.post(`${this.baseURL}/api/v1/auth/login`, {
      form: {
        username: email,
        password: password,
      },
    });

    if (response.ok()) {
      const data = await response.json();
      return data.access_token;
    }

    throw new Error(`Login failed: ${response.status()}`);
  }

  /**
   * Upload a document via API
   */
  async uploadDocument(
    token: string,
    filename: string,
    content: string
  ): Promise<{ id: string; uuid: string }> {
    const formData = new FormData();
    const blob = new Blob([content], { type: 'text/plain' });
    formData.append('file', blob, filename);
    formData.append('title', 'API Test Document');
    formData.append('description', 'Uploaded via API for testing');

    const response = await this.request.post(`${this.baseURL}/api/v1/files/upload`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      multipart: {
        file: {
          name: filename,
          mimeType: 'text/plain',
          buffer: Buffer.from(content),
        },
        title: 'API Test Document',
        description: 'Uploaded via API for testing',
      },
    });

    if (response.ok()) {
      const data = await response.json();
      return { id: data.id, uuid: data.uuid };
    }

    throw new Error(`Document upload failed: ${response.status()}`);
  }

  /**
   * Get audit logs (admin only)
   */
  async getAuditLogs(token: string, limit: number = 50): Promise<any[]> {
    const response = await this.request.get(
      `${this.baseURL}/api/v1/audit/?limit=${limit}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (response.ok()) {
      const data = await response.json();
      return data.items || data.audits || [];
    }

    return [];
  }

  /**
   * Clean up test data
   */
  async deleteUser(token: string, userId: number): Promise<void> {
    await this.request.delete(`${this.baseURL}/api/v1/users/${userId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  /**
   * Delete a document
   */
  async deleteDocument(token: string, documentId: string): Promise<void> {
    await this.request.delete(`${this.baseURL}/api/v1/files/${documentId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  /**
   * Check system health
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.request.get(`${this.baseURL}/health`);
      return response.ok();
    } catch {
      return false;
    }
  }

  /**
   * Search documents
   */
  async searchDocuments(
    token: string,
    query: string
  ): Promise<any[]> {
    const response = await this.request.get(
      `${this.baseURL}/api/v1/files/list?search=${encodeURIComponent(query)}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (response.ok()) {
      const data = await response.json();
      return data.items || data.documents || [];
    }

    return [];
  }
}


