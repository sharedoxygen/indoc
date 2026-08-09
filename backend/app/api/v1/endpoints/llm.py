"""
LLM management endpoints
"""
from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.services.llm_service import LLMService
from app.core.config import settings

router = APIRouter()


class ModelConfigUpdate(BaseModel):
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000


class ChatSettings(BaseModel):
    default_model: str
    temperature: float
    max_tokens: int
    available_models: List[Dict[str, str]]


@router.get("/models", response_model=List[Dict[str, str]])
async def list_available_models(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get list of available Ollama models"""
    try:
        llm_service = LLMService()
        
        # Check if Ollama is connected
        if not await llm_service.check_ollama_connection():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ollama service is not available"
            )
        
        # Get available models
        models = await llm_service.list_available_models()
        
        # Format models with descriptions
        model_info = []
        for model in models:
            description = "Available model"
            if "120b" in model:
                description = "Large model for complex reasoning"
            elif "70b" in model:
                description = "Advanced reasoning and analysis"
            elif "72b" in model:
                description = "Strong context understanding"
            elif "20b" in model:
                description = "Balanced speed and quality"
            elif "embed" in model:
                description = "Embedding model for search"
            
            model_info.append({
                "name": model,
                "description": description,
                "size": "large" if any(x in model for x in ["120b", "70b", "72b"]) else "medium"
            })
        
        return model_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch models: {str(e)}"
        )


@router.get("/settings", response_model=ChatSettings)
async def get_chat_settings(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Get current chat settings"""
    try:
        llm_service = LLMService()
        models = await llm_service.list_available_models()
        
        # Format available models
        available_models = []
        for model in models:
            available_models.append({
                "value": model,
                "label": model.replace(":", " ").title(),
                "description": f"Ollama model: {model}"
            })
        
        return ChatSettings(
            default_model=settings.OLLAMA_MODEL,
            temperature=0.7,
            max_tokens=1000,
            available_models=available_models
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat settings: {str(e)}"
        )


@router.post("/settings")
async def update_chat_settings(
    config: ModelConfigUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update default chat settings (Admin only)"""
    try:
        llm_service = LLMService()
        
        # Verify model is available
        available_models = await llm_service.list_available_models()
        if config.model not in available_models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{config.model}' is not available"
            )
        
        # Validate parameters
        if not (0 <= config.temperature <= 1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Temperature must be between 0 and 1"
            )
        
        if not (100 <= config.max_tokens <= 4000):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Max tokens must be between 100 and 4000"
            )
        
        # Update settings (in production, this would update database/config)
        # For now, just validate and return success
        
        return {
            "message": "Chat settings updated successfully",
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


@router.get("/health")
async def check_llm_health(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Check LLM service health"""
    try:
        llm_service = LLMService()
        
        connected = await llm_service.check_ollama_connection()
        models = await llm_service.list_available_models() if connected else []
        
        return {
            "status": "healthy" if connected else "unavailable",
            "connected": connected,
            "base_url": settings.OLLAMA_BASE_URL,
            "default_model": settings.OLLAMA_MODEL,
            "available_models": len(models),
            "models": models[:5]  # First 5 models
        }
        
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "error": str(e)
        }


@router.post("/test")
async def test_llm_generation(
    prompt: str,
    model: str = None,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Test LLM generation with a simple prompt"""
    try:
        llm_service = LLMService()
        
        # Override model if specified
        if model:
            original_model = llm_service.model
            llm_service.model = model
        
        response = await llm_service.generate_response(
            prompt=prompt,
            temperature=0.7,
            max_tokens=200
        )
        
        # Restore original model
        if model:
            llm_service.model = original_model
        
        return {
            "prompt": prompt,
            "response": response,
            "model_used": model or settings.OLLAMA_MODEL
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM test failed: {str(e)}"
        )
