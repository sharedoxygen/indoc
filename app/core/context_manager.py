"""
Context size management for user interactions
Handles dynamic context sizing based on model capabilities, user role, and content type
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import tiktoken

logger = logging.getLogger(__name__)


class ContextPriority(Enum):
    """Priority levels for context inclusion"""
    CRITICAL = 1    # Must include (user message, key document sections)
    HIGH = 2        # Important (recent conversation, primary documents)
    MEDIUM = 3      # Useful (additional documents, older conversation)
    LOW = 4         # Optional (metadata, tangential content)


@dataclass
class ContextItem:
    """Individual context item with metadata"""
    content: str
    priority: ContextPriority
    token_count: int
    content_type: str  # 'user_message', 'document', 'conversation_history', 'metadata'
    source_id: Optional[str] = None  # Document ID, message ID, etc.


@dataclass
class ModelLimits:
    """Model-specific context limits"""
    name: str
    max_context_tokens: int
    max_output_tokens: int
    recommended_context_ratio: float = 0.75  # Use 75% of context for input, 25% for output


class ContextManager:
    """Intelligent context size management for user interactions"""
    
    def __init__(self):
        # Model context limits (dynamically populated from Ollama)
        self.model_limits = {
            # Conservative defaults - will be updated from actual model info
            "gpt-oss:20b": ModelLimits("gpt-oss:20b", 8192, 2048),
            "gpt-oss:120b": ModelLimits("gpt-oss:120b", 32768, 4096),
            "gemma3:27b": ModelLimits("gemma3:27b", 8192, 2048),
            "deepseek-r1:32b": ModelLimits("deepseek-r1:32b", 16384, 4096),
            "deepseek-r1:70b": ModelLimits("deepseek-r1:70b", 32768, 4096),
            "kimi-k2:72b": ModelLimits("kimi-k2:72b", 200000, 4096),  # Known for long context
            "qwen3:32b": ModelLimits("qwen3:32b", 32768, 4096),
            "default": ModelLimits("default", 4096, 1024)
        }
        
        # User role context allowances
        self.role_multipliers = {
            "Admin": 1.5,      # 50% more context for admins
            "Reviewer": 1.3,   # 30% more for reviewers
            "Uploader": 1.1,   # 10% more for uploaders
            "Viewer": 1.0,     # Base context
            "Compliance": 1.4  # More context for compliance analysis
        }
        
        # Initialize tokenizer for accurate counting
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None
            logger.warning("Tiktoken not available, using approximate token counting")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Approximate: 1 token ≈ 4 characters for English
            return len(text) // 4
    
    def get_model_limits(self, model_name: str) -> ModelLimits:
        """Get context limits for specific model"""
        return self.model_limits.get(model_name, self.model_limits["default"])
    
    def calculate_user_context_budget(self, model_name: str, user_role: str) -> int:
        """Calculate available context tokens for user based on model and role"""
        limits = self.get_model_limits(model_name)
        role_multiplier = self.role_multipliers.get(user_role, 1.0)
        
        # Reserve space for output
        available_input_tokens = int(limits.max_context_tokens * limits.recommended_context_ratio)
        
        # Apply role-based multiplier
        user_budget = int(available_input_tokens * role_multiplier)
        
        # Cap at model's hard limit minus output reservation
        max_input = limits.max_context_tokens - limits.max_output_tokens
        return min(user_budget, max_input)
    
    def build_context_items(
        self,
        user_message: str,
        documents: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ContextItem]:
        """Build prioritized list of context items"""
        items = []
        
        # 1. User message (CRITICAL - always included)
        user_tokens = self.count_tokens(user_message)
        items.append(ContextItem(
            content=user_message,
            priority=ContextPriority.CRITICAL,
            token_count=user_tokens,
            content_type="user_message"
        ))
        
        # 2. Document content (HIGH priority)
        for i, doc in enumerate(documents):
            content = doc.get("content", "")
            if content.strip():
                tokens = self.count_tokens(content)
                items.append(ContextItem(
                    content=f"Document: {doc.get('title', f'Document {i+1}')}\n{content}",
                    priority=ContextPriority.HIGH,
                    token_count=tokens,
                    content_type="document",
                    source_id=doc.get("id")
                ))
        
        # 3. Document Library Statistics (HIGH priority - always include for context awareness)
        if metadata and metadata.get("library_stats"):
            stats = metadata["library_stats"]
            stats_text = f"\n📊 Document Library Overview:\n"
            stats_text += f"Total Documents: {stats.get('total_documents', 0):,}\n"
            if stats.get('breakdown'):
                stats_text += "Breakdown by Type:\n"
                for file_type, count in sorted(stats['breakdown'].items(), key=lambda x: x[1], reverse=True):
                    stats_text += f"  - {file_type.upper()}: {count:,} documents\n"
            
            tokens = self.count_tokens(stats_text)
            items.append(ContextItem(
                content=stats_text,
                priority=ContextPriority.HIGH,
                token_count=tokens,
                content_type="library_statistics"
            ))
        
        # 4. Recent conversation history (MEDIUM priority)
        if conversation_history:
            # Include last N messages based on token budget
            for msg in conversation_history[-5:]:  # Last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content.strip():
                    tokens = self.count_tokens(content)
                    items.append(ContextItem(
                        content=f"{role.title()}: {content}",
                        priority=ContextPriority.MEDIUM,
                        token_count=tokens,
                        content_type="conversation_history"
                    ))
        
        # 5. Metadata (LOW priority)
        if metadata:
            meta_str = f"Metadata: {str(metadata)}"
            tokens = self.count_tokens(meta_str)
            items.append(ContextItem(
                content=meta_str,
                priority=ContextPriority.LOW,
                token_count=tokens,
                content_type="metadata"
            ))
        
        return items
    
    def optimize_context(
        self,
        context_items: List[ContextItem],
        token_budget: int,
        preserve_document_balance: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Optimize context to fit within token budget while preserving important information
        
        Returns:
            - Optimized context string
            - Context metadata (what was included/excluded)
        """
        # Sort by priority
        sorted_items = sorted(context_items, key=lambda x: x.priority.value)
        
        included_items = []
        total_tokens = 0
        
        # Always include CRITICAL items
        for item in sorted_items:
            if item.priority == ContextPriority.CRITICAL:
                included_items.append(item)
                total_tokens += item.token_count
        
        # Add HIGH priority items (documents) with balancing
        document_items = [item for item in sorted_items if item.content_type == "document"]
        if preserve_document_balance and document_items:
            # Distribute remaining budget equally among documents
            remaining_budget = token_budget - total_tokens
            tokens_per_doc = remaining_budget // len(document_items) if document_items else 0
            
            for item in document_items:
                if total_tokens + min(item.token_count, tokens_per_doc) <= token_budget:
                    if item.token_count > tokens_per_doc:
                        # Truncate document content to fit budget
                        truncated_content = self._truncate_content(item.content, tokens_per_doc)
                        truncated_item = ContextItem(
                            content=truncated_content,
                            priority=item.priority,
                            token_count=tokens_per_doc,
                            content_type=item.content_type,
                            source_id=item.source_id
                        )
                        included_items.append(truncated_item)
                        total_tokens += tokens_per_doc
                    else:
                        included_items.append(item)
                        total_tokens += item.token_count
        else:
            # Standard priority-based inclusion
            for item in sorted_items:
                if item.priority != ContextPriority.CRITICAL:  # Already added
                    if total_tokens + item.token_count <= token_budget:
                        included_items.append(item)
                        total_tokens += item.token_count
                    else:
                        break
        
        # Build final context string
        context_parts = []
        document_count = 0
        history_count = 0
        
        for item in included_items:
            if item.content_type == "document":
                document_count += 1
                context_parts.append(item.content)
            elif item.content_type == "conversation_history":
                if history_count == 0:
                    context_parts.append("\nRecent conversation:")
                context_parts.append(item.content)
                history_count += 1
            elif item.content_type == "user_message":
                context_parts.insert(0, f"Current question: {item.content}")
        
        final_context = "\n\n".join(context_parts)
        
        # Context metadata for debugging/monitoring and lightweight source tracing
        sources = []
        for item in included_items:
            if item.content_type == "document" and item.source_id:
                sources.append({"id": item.source_id})

        context_metadata = {
            "total_tokens_used": total_tokens,
            "token_budget": token_budget,
            "utilization_percent": round((total_tokens / token_budget) * 100, 1),
            "documents_included": document_count,
            "history_messages_included": history_count,
            "items_included": len(included_items),
            "items_excluded": len(context_items) - len(included_items),
            "sources": sources
        }
        
        return final_context, context_metadata
    
    def _truncate_content(self, content: str, target_tokens: int) -> str:
        """Intelligently truncate content to fit token budget"""
        if self.count_tokens(content) <= target_tokens:
            return content
        
        # Approximate character count for target tokens
        target_chars = target_tokens * 4
        
        if len(content) <= target_chars:
            return content
        
        # Try to truncate at sentence boundaries
        truncated = content[:target_chars]
        last_sentence = truncated.rfind('. ')
        
        if last_sentence > target_chars * 0.7:  # If we can keep 70% and end at sentence
            return truncated[:last_sentence + 1] + "\n\n[Content truncated to fit context limit]"
        else:
            return truncated + "\n\n[Content truncated to fit context limit]"
    
    async def update_model_limits_from_ollama(self, ollama_models: List[Dict[str, Any]]):
        """Update model limits based on actual Ollama model information"""
        for model_info in ollama_models:
            name = model_info.get("name", "")
            if name:
                # Extract context size from model details if available
                details = model_info.get("details", {})
                param_size = details.get("parameter_size", "")
                
                # Estimate context size based on parameter count
                if "120b" in name.lower() or "70b" in name.lower():
                    context_size = 32768
                elif "32b" in name.lower() or "27b" in name.lower():
                    context_size = 16384
                elif "20b" in name.lower():
                    context_size = 8192
                elif "kimi" in name.lower():
                    context_size = 200000  # Kimi is known for long context
                else:
                    context_size = 8192  # Conservative default
                
                self.model_limits[name] = ModelLimits(
                    name=name,
                    max_context_tokens=context_size,
                    max_output_tokens=min(4096, context_size // 4)
                )
        
        logger.info(f"Updated context limits for {len(ollama_models)} models")

    def safe_extract_sources(self, context_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Safely extract lightweight sources list from context metadata."""
        try:
            sources = context_metadata.get("sources", []) if context_metadata else []
            if isinstance(sources, list):
                return sources
            return []
        except Exception:
            return []


# Global context manager instance
context_manager = ContextManager()
