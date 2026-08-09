"""
Performance tests using Locust
"""
import json
import random
from locust import HttpUser, task, between


class InDocUser(HttpUser):
    """Simulated user for load testing"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Login when user starts"""
        # Create test user or login with existing one
        self.login()
    
    def login(self):
        """Login to get authentication token"""
        response = self.client.post("/api/v1/auth/login", data={
            "username": "test@example.com",
            "password": "testpassword"
        })
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {token}"})
        else:
            # Try to register if login fails
            self.client.post("/api/v1/auth/register", json={
                "email": f"loadtest{random.randint(1000,9999)}@example.com",
                "username": f"loadtest{random.randint(1000,9999)}",
                "password": "testpassword",
                "full_name": "Load Test User"
            })
    
    @task(3)
    def view_health(self):
        """Check health endpoint"""
        self.client.get("/health")
    
    @task(2)
    def list_documents(self):
        """List user documents"""
        self.client.get("/api/v1/files/list")
    
    @task(1)
    def search_documents(self):
        """Search documents"""
        queries = [
            "test document",
            "important",
            "contract",
            "report",
            "meeting notes"
        ]
        query = random.choice(queries)
        self.client.post("/api/v1/search/query", json={
            "query": query,
            "limit": 10
        })
    
    @task(1)
    def get_user_profile(self):
        """Get current user profile"""
        self.client.get("/api/v1/users/me")


class AdminUser(HttpUser):
    """Admin user for testing admin endpoints"""
    
    wait_time = between(2, 5)
    weight = 1  # Lower weight means fewer admin users
    
    def on_start(self):
        """Login as admin"""
        response = self.client.post("/api/v1/auth/login", data={
            "username": "admin@example.com", 
            "password": "adminpassword"
        })
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    @task(2)
    def list_users(self):
        """List all users (admin only)"""
        self.client.get("/api/v1/users/")
    
    @task(1)
    def get_system_stats(self):
        """Get system statistics"""
        self.client.get("/api/v1/admin/stats")
    
    @task(1)
    def view_audit_logs(self):
        """View audit logs"""
        self.client.get("/api/v1/audit/logs")


class FileUploadUser(HttpUser):
    """User focused on file upload testing"""
    
    wait_time = between(5, 10)
    weight = 1  # Fewer upload users
    
    def on_start(self):
        """Login for file operations"""
        response = self.client.post("/api/v1/auth/login", data={
            "username": "uploader@example.com",
            "password": "uploaderpassword"
        })
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    @task(1)
    def upload_small_file(self):
        """Upload a small test file"""
        test_content = f"Test file content {random.randint(1000, 9999)}\n" * 100
        
        files = {
            'file': ('test_document.txt', test_content, 'text/plain')
        }
        data = {
            'title': f'Load Test Document {random.randint(1000, 9999)}',
            'description': 'Generated during load testing'
        }
        
        self.client.post("/api/v1/files/upload", files=files, data=data)
