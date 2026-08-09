#!/usr/bin/env python3
"""
E2E Test Runner for inDoc Application

This script runs comprehensive end-to-end tests for all user roles and workflows.
"""

import asyncio
import sys
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import aiohttp
import tempfile
import io

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class E2ETestRunner:
    """Run comprehensive E2E tests for inDoc application"""
    
    def __init__(self, base_url: str = "http://localhost:5173"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.session = None
        self.test_tokens = {}
        self.test_results = {}
        
        # Test user credentials
        # Note: Passwords are now randomly generated. 
        # Use the output from seed data generation or set environment variables.
        import os
        self.test_users = {
            "admin": {"username": "admin", "password": os.getenv("ADMIN_PASSWORD", "admin123")},
            "admin_test": {"username": "admin_primary", "password": os.getenv("ADMIN_TEST_PASSWORD", "admin123")},
            "reviewer": {"username": "legal_reviewer", "password": os.getenv("REVIEWER_PASSWORD", "review123")},
            "uploader": {"username": "hr_uploader", "password": os.getenv("UPLOADER_PASSWORD", "upload123")},
            "viewer": {"username": "external_viewer", "password": os.getenv("VIEWER_PASSWORD", "view123")},
            "compliance": {"username": "compliance_officer", "password": os.getenv("COMPLIANCE_PASSWORD", "comply123")}
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def login_user(self, user_key: str) -> str:
        """Login user and return JWT token"""
        if user_key in self.test_tokens:
            return self.test_tokens[user_key]
        
        credentials = self.test_users[user_key]
        
        data = aiohttp.FormData()
        data.add_field('username', credentials['username'])
        data.add_field('password', credentials['password'])
        
        async with self.session.post(f"{self.api_base}/auth/login", data=data) as response:
            if response.status == 200:
                result = await response.json()
                token = result.get("access_token")
                self.test_tokens[user_key] = token
                logger.info(f"✅ Logged in {user_key}: {credentials['username']}")
                return token
            else:
                error = await response.text()
                logger.error(f"❌ Login failed for {user_key}: {error}")
                return None
    
    async def make_authenticated_request(self, method: str, endpoint: str, user_key: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API request"""
        token = await self.login_user(user_key)
        if not token:
            return {"error": "Authentication failed", "status": 401}
        
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        kwargs["headers"] = headers
        
        url = f"{self.api_base}{endpoint}"
        
        async with self.session.request(method, url, **kwargs) as response:
            try:
                result = await response.json()
                return {"data": result, "status": response.status}
            except:
                text = await response.text()
                return {"data": text, "status": response.status}
    
    async def test_admin_workflows(self) -> Dict[str, Any]:
        """Test complete admin workflows"""
        logger.info("🔧 Testing Admin workflows...")
        results = {}
        
        # Test 1: User management
        logger.info("  Testing user management...")
        
        # List users
        response = await self.make_authenticated_request("GET", "/users", "admin")
        results["list_users"] = response["status"] == 200
        
        # Get user statistics
        response = await self.make_authenticated_request("GET", "/users/statistics", "admin")
        results["user_statistics"] = response["status"] == 200
        
        # Test 2: System settings
        logger.info("  Testing system settings...")
        
        # Get settings
        response = await self.make_authenticated_request("GET", "/settings", "admin")
        results["get_settings"] = response["status"] == 200
        
        # Get admin settings
        response = await self.make_authenticated_request("GET", "/settings/admin", "admin")
        results["get_admin_settings"] = response["status"] == 200
        
        # Test 3: Document management
        logger.info("  Testing document management...")
        
        # List all documents
        response = await self.make_authenticated_request("GET", "/files", "admin")
        results["list_documents"] = response["status"] == 200
        
        # Test 4: Audit logs
        logger.info("  Testing audit access...")
        
        # Get audit logs
        response = await self.make_authenticated_request("GET", "/audit/logs", "admin")
        results["audit_logs"] = response["status"] == 200
        
        logger.info(f"  Admin tests: {sum(results.values())}/{len(results)} passed")
        return results
    
    async def test_reviewer_workflows(self) -> Dict[str, Any]:
        """Test reviewer workflows"""
        logger.info("📋 Testing Reviewer workflows...")
        results = {}
        
        # Test 1: Document access
        logger.info("  Testing document access...")
        
        # List documents (should see all)
        response = await self.make_authenticated_request("GET", "/files", "reviewer")
        results["list_documents"] = response["status"] == 200
        
        # Test 2: Search functionality
        logger.info("  Testing search functionality...")
        
        # Search documents
        search_data = {"query": "policy", "limit": 10}
        response = await self.make_authenticated_request("POST", "/search/query", "reviewer", json=search_data)
        results["search_documents"] = response["status"] == 200
        
        # Test 3: Cannot upload (should fail)
        logger.info("  Testing upload restrictions...")
        
        # Try to upload (should be forbidden)
        test_file = b"Test content for reviewer upload attempt"
        data = aiohttp.FormData()
        data.add_field('file', io.BytesIO(test_file), filename='test.txt', content_type='text/plain')
        
        response = await self.make_authenticated_request("POST", "/files", "reviewer", data=data)
        results["upload_forbidden"] = response["status"] == 403  # Should be forbidden
        
        # Test 4: User management restrictions
        logger.info("  Testing user management restrictions...")
        
        # Try to list users (should be forbidden)
        response = await self.make_authenticated_request("GET", "/users", "reviewer")
        results["user_mgmt_forbidden"] = response["status"] == 403
        
        logger.info(f"  Reviewer tests: {sum(results.values())}/{len(results)} passed")
        return results
    
    async def test_uploader_workflows(self) -> Dict[str, Any]:
        """Test uploader workflows"""
        logger.info("📤 Testing Uploader workflows...")
        results = {}
        
        # Test 1: File upload
        logger.info("  Testing file upload...")
        
        # Create test file
        test_content = "This is a test document uploaded by E2E testing framework."
        test_file = test_content.encode('utf-8')
        
        data = aiohttp.FormData()
        data.add_field('file', io.BytesIO(test_file), filename='e2e_test_upload.txt', content_type='text/plain')
        data.add_field('title', 'E2E Test Document')
        data.add_field('description', 'Document uploaded during E2E testing')
        data.add_field('tags', 'e2e,testing,automation')
        
        response = await self.make_authenticated_request("POST", "/files", "uploader", data=data)
        results["file_upload"] = response["status"] == 200
        
        if response["status"] == 200:
            uploaded_doc_id = response["data"].get("id")
            logger.info(f"    Uploaded document ID: {uploaded_doc_id}")
        
        # Test 2: List own documents
        logger.info("  Testing document listing...")
        
        response = await self.make_authenticated_request("GET", "/files", "uploader")
        results["list_own_documents"] = response["status"] == 200
        
        # Test 3: Search functionality
        logger.info("  Testing search access...")
        
        search_data = {"query": "test", "limit": 5}
        response = await self.make_authenticated_request("POST", "/search/query", "uploader", json=search_data)
        results["search_access"] = response["status"] == 200
        
        # Test 4: Admin restrictions
        logger.info("  Testing admin restrictions...")
        
        # Try to access admin settings (should fail)
        response = await self.make_authenticated_request("GET", "/settings/admin", "uploader")
        results["admin_forbidden"] = response["status"] == 403
        
        # Try to manage users (should fail)
        response = await self.make_authenticated_request("GET", "/users", "uploader")
        results["user_mgmt_forbidden"] = response["status"] == 403
        
        logger.info(f"  Uploader tests: {sum(results.values())}/{len(results)} passed")
        return results
    
    async def test_viewer_workflows(self) -> Dict[str, Any]:
        """Test viewer workflows"""
        logger.info("👁️ Testing Viewer workflows...")
        results = {}
        
        # Test 1: Document viewing (limited)
        logger.info("  Testing document viewing...")
        
        response = await self.make_authenticated_request("GET", "/files", "viewer")
        results["view_documents"] = response["status"] == 200
        
        # Test 2: Search functionality
        logger.info("  Testing search functionality...")
        
        search_data = {"query": "manual", "limit": 10}
        response = await self.make_authenticated_request("POST", "/search/query", "viewer", json=search_data)
        results["search_documents"] = response["status"] == 200
        
        # Test 3: Upload restrictions (should fail)
        logger.info("  Testing upload restrictions...")
        
        test_file = b"Viewer should not be able to upload this"
        data = aiohttp.FormData()
        data.add_field('file', io.BytesIO(test_file), filename='viewer_test.txt', content_type='text/plain')
        
        response = await self.make_authenticated_request("POST", "/files", "viewer", data=data)
        results["upload_forbidden"] = response["status"] == 403
        
        # Test 4: Admin restrictions (should fail)
        logger.info("  Testing admin restrictions...")
        
        response = await self.make_authenticated_request("GET", "/users", "viewer")
        results["admin_forbidden"] = response["status"] == 403
        
        response = await self.make_authenticated_request("GET", "/settings/admin", "viewer")
        results["settings_forbidden"] = response["status"] == 403
        
        # Test 5: Chat functionality
        logger.info("  Testing chat functionality...")
        
        # This would test WebSocket chat - simplified for HTTP testing
        chat_data = {"message": "What documents are available?"}
        # Note: Chat endpoint may need to be implemented for HTTP testing
        
        logger.info(f"  Viewer tests: {sum(results.values())}/{len(results)} passed")
        return results
    
    async def test_compliance_workflows(self) -> Dict[str, Any]:
        """Test compliance workflows"""
        logger.info("⚖️ Testing Compliance workflows...")
        results = {}
        
        # Test 1: Audit log access
        logger.info("  Testing audit log access...")
        
        response = await self.make_authenticated_request("GET", "/audit/logs", "compliance")
        results["audit_access"] = response["status"] == 200
        
        # Test 2: Document access for compliance
        logger.info("  Testing document access...")
        
        response = await self.make_authenticated_request("GET", "/files", "compliance")
        results["document_access"] = response["status"] == 200
        
        # Test 3: Export functionality
        logger.info("  Testing export functionality...")
        
        export_data = {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "format": "csv"
        }
        response = await self.make_authenticated_request("POST", "/audit/logs/export", "compliance", json=export_data)
        results["export_logs"] = response["status"] == 200
        
        # Test 4: Upload restrictions (should fail)
        logger.info("  Testing upload restrictions...")
        
        test_file = b"Compliance should not upload documents"
        data = aiohttp.FormData()
        data.add_field('file', io.BytesIO(test_file), filename='compliance_test.txt', content_type='text/plain')
        
        response = await self.make_authenticated_request("POST", "/files", "compliance", data=data)
        results["upload_forbidden"] = response["status"] == 403
        
        # Test 5: User management restrictions
        logger.info("  Testing user management restrictions...")
        
        response = await self.make_authenticated_request("GET", "/users", "compliance")
        results["user_mgmt_forbidden"] = response["status"] == 403
        
        logger.info(f"  Compliance tests: {sum(results.values())}/{len(results)} passed")
        return results
    
    async def test_authentication_flows(self) -> Dict[str, Any]:
        """Test authentication and authorization flows"""
        logger.info("🔐 Testing Authentication flows...")
        results = {}
        
        # Test 1: Valid login for each role
        logger.info("  Testing valid logins...")
        for user_key in self.test_users.keys():
            token = await self.login_user(user_key)
            results[f"login_{user_key}"] = token is not None
        
        # Test 2: Invalid login
        logger.info("  Testing invalid login...")
        data = aiohttp.FormData()
        data.add_field('username', 'invalid_user')
        data.add_field('password', 'wrong_password')
        
        async with self.session.post(f"{self.api_base}/auth/login", data=data) as response:
            results["invalid_login"] = response.status == 401
        
        # Test 3: Token validation
        logger.info("  Testing token validation...")
        
        # Test with valid token
        token = await self.login_user("admin")
        headers = {"Authorization": f"Bearer {token}"}
        
        async with self.session.get(f"{self.api_base}/auth/me", headers=headers) as response:
            results["valid_token"] = response.status == 200
        
        # Test with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        async with self.session.get(f"{self.api_base}/auth/me", headers=headers) as response:
            results["invalid_token"] = response.status == 401
        
        # Test 4: Unauthenticated access
        logger.info("  Testing unauthenticated access...")
        
        async with self.session.get(f"{self.api_base}/auth/me") as response:
            results["no_auth"] = response.status == 401
        
        logger.info(f"  Auth tests: {sum(results.values())}/{len(results)} passed")
        return results
    
    async def test_document_operations(self) -> Dict[str, Any]:
        """Test document operations across roles"""
        logger.info("📄 Testing Document operations...")
        results = {}
        
        # Test 1: Upload different file types
        logger.info("  Testing file type uploads...")
        
        file_types = [
            ("test.txt", "text/plain", b"Text file content for E2E testing"),
            ("test.json", "application/json", b'{"test": "JSON content for E2E testing"}'),
            ("test.html", "text/html", b"<html><body><h1>HTML content for E2E testing</h1></body></html>")
        ]
        
        upload_results = []
        for filename, content_type, content in file_types:
            data = aiohttp.FormData()
            data.add_field('file', io.BytesIO(content), filename=filename, content_type=content_type)
            data.add_field('title', f'E2E Test {filename}')
            data.add_field('description', f'E2E testing document: {filename}')
            
            response = await self.make_authenticated_request("POST", "/files", "uploader", data=data)
            upload_results.append(response["status"] == 200)
            
            if response["status"] == 200:
                logger.info(f"    ✅ Uploaded {filename}")
            else:
                logger.error(f"    ❌ Failed to upload {filename}: {response}")
        
        results["file_uploads"] = all(upload_results)
        
        # Test 2: Document listing by different roles
        logger.info("  Testing document access by role...")
        
        for role in ["admin", "reviewer", "uploader", "viewer"]:
            response = await self.make_authenticated_request("GET", "/files", role)
            results[f"list_docs_{role}"] = response["status"] == 200
            
            if response["status"] == 200:
                doc_count = len(response["data"])
                logger.info(f"    {role}: Can see {doc_count} documents")
        
        # Test 3: Search functionality
        logger.info("  Testing search functionality...")
        
        search_queries = [
            {"query": "test", "limit": 5},
            {"query": "policy manual", "limit": 10},
            {"query": "financial report", "limit": 3}
        ]
        
        search_results = []
        for query in search_queries:
            response = await self.make_authenticated_request("POST", "/search/query", "admin", json=query)
            search_results.append(response["status"] == 200)
        
        results["search_functionality"] = all(search_results)
        
        logger.info(f"  Document tests: {sum(results.values())}/{len(results)} passed")
        return results
    
    async def test_permission_enforcement(self) -> Dict[str, Any]:
        """Test role-based permission enforcement"""
        logger.info("🛡️ Testing Permission enforcement...")
        results = {}
        
        # Test permission matrix
        permission_tests = [
            # (role, endpoint, method, expected_status)
            ("viewer", "/users", "GET", 403),           # Viewer cannot list users
            ("viewer", "/settings/admin", "GET", 403),  # Viewer cannot access admin settings
            ("uploader", "/users", "GET", 403),         # Uploader cannot list users
            ("uploader", "/audit/logs", "GET", 403),    # Uploader cannot access audit logs
            ("reviewer", "/users", "GET", 403),         # Reviewer cannot list users
            ("compliance", "/users", "GET", 403),       # Compliance cannot list users (admin only)
            ("admin", "/users", "GET", 200),            # Admin can list users
            ("admin", "/settings/admin", "GET", 200),   # Admin can access admin settings
            ("compliance", "/audit/logs", "GET", 200),  # Compliance can access audit logs
        ]
        
        for role, endpoint, method, expected_status in permission_tests:
            response = await self.make_authenticated_request(method, endpoint, role)
            test_name = f"{role}_{endpoint.replace('/', '_')}_{method}"
            results[test_name] = response["status"] == expected_status
            
            if response["status"] == expected_status:
                logger.info(f"    ✅ {role} {method} {endpoint}: {response['status']} (expected)")
            else:
                logger.error(f"    ❌ {role} {method} {endpoint}: {response['status']} (expected {expected_status})")
        
        logger.info(f"  Permission tests: {sum(results.values())}/{len(results)} passed")
        return results
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test error handling and edge cases"""
        logger.info("⚠️ Testing Error handling...")
        results = {}
        
        # Test 1: Invalid endpoints
        logger.info("  Testing invalid endpoints...")
        
        response = await self.make_authenticated_request("GET", "/nonexistent", "admin")
        results["invalid_endpoint"] = response["status"] == 404
        
        # Test 2: Malformed requests
        logger.info("  Testing malformed requests...")
        
        # Invalid JSON
        async with self.session.post(f"{self.api_base}/search/query", 
                                   headers={"Authorization": f"Bearer {await self.login_user('admin')}"},
                                   data="invalid json") as response:
            results["invalid_json"] = response.status in [400, 422]
        
        # Test 3: Large file upload (should fail if over limit)
        logger.info("  Testing file size limits...")
        
        # Create file larger than limit (100MB + 1KB)
        large_content = b"x" * (100 * 1024 * 1024 + 1024)
        data = aiohttp.FormData()
        data.add_field('file', io.BytesIO(large_content), filename='large_file.txt', content_type='text/plain')
        
        response = await self.make_authenticated_request("POST", "/files", "uploader", data=data)
        results["file_size_limit"] = response["status"] in [400, 413, 422]  # Should be rejected
        
        logger.info(f"  Error handling tests: {sum(results.values())}/{len(results)} passed")
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all E2E tests"""
        logger.info("🚀 Starting comprehensive E2E testing...")
        
        all_results = {}
        
        try:
            # Run test suites
            all_results["authentication"] = await self.test_authentication_flows()
            all_results["admin_workflows"] = await self.test_admin_workflows()
            all_results["reviewer_workflows"] = await self.test_reviewer_workflows()
            all_results["uploader_workflows"] = await self.test_uploader_workflows()
            all_results["viewer_workflows"] = await self.test_viewer_workflows()
            all_results["compliance_workflows"] = await self.test_compliance_workflows()
            all_results["permission_enforcement"] = await self.test_permission_enforcement()
            all_results["error_handling"] = await self.test_error_handling()
            
            # Calculate overall results
            total_tests = sum(len(suite) for suite in all_results.values())
            passed_tests = sum(sum(suite.values()) for suite in all_results.values())
            
            logger.info("=" * 60)
            logger.info("🎯 E2E TEST RESULTS SUMMARY")
            logger.info("=" * 60)
            
            for suite_name, suite_results in all_results.items():
                passed = sum(suite_results.values())
                total = len(suite_results)
                status = "✅ PASS" if passed == total else "❌ FAIL"
                logger.info(f"{suite_name:25} | {passed:2}/{total:2} | {status}")
            
            logger.info("-" * 60)
            overall_status = "✅ ALL TESTS PASSED" if passed_tests == total_tests else "❌ SOME TESTS FAILED"
            logger.info(f"{'OVERALL':25} | {passed_tests:2}/{total_tests:2} | {overall_status}")
            logger.info("=" * 60)
            
            return all_results
            
        except Exception as e:
            logger.error(f"❌ E2E testing failed: {str(e)}")
            return {"error": str(e)}


async def main():
    """Main function to run E2E tests"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
E2E Test Runner for inDoc Application

Usage:
  python e2e_test_runner.py              # Run all tests
  python e2e_test_runner.py --url <url>  # Use custom base URL
  
Prerequisites:
  1. All services running (make local-e2e)
  2. Seed data generated (python seed_data_generator.py)
  3. Application accessible at base URL
        """)
        return
    
    base_url = "http://localhost:5173"
    if len(sys.argv) > 2 and sys.argv[1] == "--url":
        base_url = sys.argv[2]
    
    logger.info(f"🎯 Running E2E tests against: {base_url}")
    
    async with E2ETestRunner(base_url) as runner:
        results = await runner.run_all_tests()
        
        # Save results to file
        results_file = Path("e2e_test_results.json")
        results_file.write_text(json.dumps(results, indent=2))
        logger.info(f"📄 Test results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())
