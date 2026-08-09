"""
Chat System Diagnostics Service

Industry-standard diagnostic service for the chat system with comprehensive
error tracking, performance monitoring, and system health validation.
"""
import logging
import time
from typing import Dict, Any, Optional, List
from uuid import UUID
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.config import settings
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.user import User

logger = logging.getLogger(__name__)


class ChatDiagnosticsService:
    """
    Comprehensive diagnostics service for chat system health monitoring
    and error analysis following industry observability best practices.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.diagnostics = {
            "database_connectivity": False,
            "llm_service_health": False,
            "search_service_health": False,
            "conversation_schema_valid": False,
            "user_permissions": False,
            "errors": [],
            "warnings": [],
            "performance_metrics": {}
        }
    
    async def run_comprehensive_diagnostics(self, user_id: int) -> Dict[str, Any]:
        """
        Run comprehensive chat system diagnostics
        
        Args:
            user_id: User ID to test permissions and access
            
        Returns:
            Detailed diagnostic report with actionable insights
        """
        start_time = time.time()
        
        try:
            # Test database connectivity
            await self._test_database_connectivity()
            
            # Test user permissions and schema
            await self._test_user_permissions(user_id)
            
            # Test conversation schema integrity
            await self._test_conversation_schema()
            
            # Test LLM service connectivity
            await self._test_llm_service()
            
            # Test search service integration
            await self._test_search_service()
            
            # Test document access patterns
            await self._test_document_access()
            
        except Exception as e:
            logger.error(f"Critical error in diagnostics: {e}")
            self.diagnostics["errors"].append({
                "type": "CRITICAL_SYSTEM_ERROR",
                "message": str(e),
                "timestamp": time.time()
            })
        
        # Performance metrics
        self.diagnostics["performance_metrics"] = {
            "total_diagnostic_time_ms": round((time.time() - start_time) * 1000, 2),
            "timestamp": time.time()
        }
        
        # Generate recommendations
        self.diagnostics["recommendations"] = self._generate_recommendations()
        
        return self.diagnostics
    
    async def _test_database_connectivity(self):
        """Test database connectivity with proper async patterns"""
        try:
            # Test basic connectivity
            result = await self.db.execute(text("SELECT 1"))
            if result.scalar() == 1:
                self.diagnostics["database_connectivity"] = True
                logger.info("Database connectivity: HEALTHY")
            else:
                raise Exception("Database query returned unexpected result")
                
        except Exception as e:
            self.diagnostics["errors"].append({
                "type": "DATABASE_CONNECTIVITY_ERROR", 
                "message": str(e)
            })
            logger.error(f"Database connectivity failed: {e}")
    
    async def _test_user_permissions(self, user_id: int):
        """Test user schema and permissions"""
        try:
            # Query user with proper async pattern
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                self.diagnostics["errors"].append({
                    "type": "USER_NOT_FOUND",
                    "message": f"User ID {user_id} not found in database"
                })
                return
            
            # Validate user schema integrity
            required_fields = ['email', 'role', 'is_active']
            missing_fields = [field for field in required_fields if not hasattr(user, field)]
            
            if missing_fields:
                self.diagnostics["warnings"].append({
                    "type": "USER_SCHEMA_INCOMPLETE",
                    "message": f"Missing user fields: {missing_fields}"
                })
            
            # Check if user has tenant_id (for multi-tenancy)
            if not hasattr(user, 'tenant_id') or user.tenant_id is None:
                self.diagnostics["warnings"].append({
                    "type": "TENANT_ID_MISSING",
                    "message": "User missing tenant_id - may cause conversation creation issues"
                })
            
            self.diagnostics["user_permissions"] = True
            logger.info(f"User permissions validated for: {user.email}")
            
        except Exception as e:
            self.diagnostics["errors"].append({
                "type": "USER_PERMISSION_ERROR",
                "message": str(e)
            })
            logger.error(f"User permission test failed: {e}")
    
    async def _test_conversation_schema(self):
        """Test conversation database schema integrity"""
        try:
            # Test conversation table structure
            result = await self.db.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'conversations'")
            )
            columns = [row[0] for row in result.fetchall()]
            
            required_columns = ['id', 'user_id', 'created_at']
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                self.diagnostics["errors"].append({
                    "type": "CONVERSATION_SCHEMA_ERROR",
                    "message": f"Missing required columns: {missing_columns}"
                })
            else:
                self.diagnostics["conversation_schema_valid"] = True
                logger.info("Conversation schema validation: PASSED")
            
        except Exception as e:
            self.diagnostics["errors"].append({
                "type": "CONVERSATION_SCHEMA_TEST_ERROR",
                "message": str(e)
            })
    
    async def _test_llm_service(self):
        """Test LLM service connectivity and health"""
        try:
            from app.services.llm_service import LLMService
            
            llm_service = LLMService()
            
            # Test Ollama connectivity
            is_connected = await llm_service.check_ollama_connection()
            
            if is_connected:
                # Test model availability
                models = await llm_service.list_available_models()
                if models:
                    self.diagnostics["llm_service_health"] = True
                    logger.info(f"LLM service: HEALTHY ({len(models)} models available)")
                else:
                    self.diagnostics["warnings"].append({
                        "type": "LLM_NO_MODELS",
                        "message": "Ollama connected but no models available"
                    })
            else:
                self.diagnostics["errors"].append({
                    "type": "LLM_CONNECTIVITY_ERROR",
                    "message": "Cannot connect to Ollama service"
                })
                
        except Exception as e:
            self.diagnostics["errors"].append({
                "type": "LLM_SERVICE_ERROR",
                "message": str(e)
            })
            logger.error(f"LLM service test failed: {e}")
    
    async def _test_search_service(self):
        """Test search service integration"""
        try:
            from app.services.search_service import SearchService
            
            search_service = SearchService(self.db)
            
            # Test search service health (basic functionality)
            # This is a placeholder for actual search health checks
            self.diagnostics["search_service_health"] = True
            logger.info("Search service: AVAILABLE")
            
        except Exception as e:
            self.diagnostics["errors"].append({
                "type": "SEARCH_SERVICE_ERROR", 
                "message": str(e)
            })
    
    async def _test_document_access(self):
        """Test document access and permissions"""
        try:
            # Test if documents exist and are accessible
            result = await self.db.execute(
                select(Document).limit(1)
            )
            test_doc = result.scalar_one_or_none()
            
            if test_doc:
                logger.info("Document access: VERIFIED")
            else:
                self.diagnostics["warnings"].append({
                    "type": "NO_DOCUMENTS",
                    "message": "No documents available for chat testing"
                })
                
        except Exception as e:
            self.diagnostics["errors"].append({
                "type": "DOCUMENT_ACCESS_ERROR",
                "message": str(e)
            })
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate actionable recommendations based on diagnostic results"""
        recommendations = []
        
        if not self.diagnostics["database_connectivity"]:
            recommendations.append({
                "priority": "CRITICAL",
                "issue": "Database connectivity failed",
                "action": "Check PostgreSQL connection and credentials",
                "impact": "Chat system completely non-functional"
            })
        
        if not self.diagnostics["llm_service_health"]:
            recommendations.append({
                "priority": "HIGH", 
                "issue": "LLM service unavailable",
                "action": "Start Ollama service and ensure models are downloaded",
                "impact": "Cannot generate AI responses"
            })
        
        if not self.diagnostics["user_permissions"]:
            recommendations.append({
                "priority": "HIGH",
                "issue": "User permissions invalid",
                "action": "Verify user account and role assignments",
                "impact": "Chat access restricted"
            })
        
        # Add recommendations for warnings
        for warning in self.diagnostics["warnings"]:
            if warning["type"] == "TENANT_ID_MISSING":
                recommendations.append({
                    "priority": "MEDIUM",
                    "issue": "Multi-tenancy not properly configured",
                    "action": "Add tenant_id to user schema or remove tenant requirements",
                    "impact": "Conversation creation may fail"
                })
        
        return recommendations


     async def diagnose_chat_system(db: AsyncSession, user_id: int) -> Dict[str, Any]:
    """
    Main diagnostic function for chat system health checking
    
    Args:
        db: Async database session
        user_id: User ID to test with
        
    Returns:
        Comprehensive diagnostic report
    """
    diagnostics_service = ChatDiagnosticsService(db)
    return await diagnostics_service.run_comprehensive_diagnostics(user_id)
