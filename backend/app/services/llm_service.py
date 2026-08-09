"""
LLM Service for handling language model interactions with Ollama
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import httpx
import asyncio
from app.core.config import settings
import re

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Ollama Language Models"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.LLM_TIMEOUT_S
        
    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """
        Generate a response from the LLM
        
        Args:
            prompt: The user prompt
            context: Optional context to include
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            
        Returns:
            Generated response text
        """
        try:
            # Build the full prompt with context
            full_prompt = self._build_prompt(prompt, context)
            
            # Dynamically select model if not provided
            selected_model = model
            if not selected_model:
                try:
                    require_code, require_vision = self._detect_capabilities(prompt)
                    selected_model = await self._pick_model(
                        require_code=require_code,
                        require_vision=require_vision
                    )
                except Exception as e:
                    logger.warning(
                        f"Dynamic model selection failed ({e}); "
                        f"falling back to configured model {self.model}"
                    )
                    selected_model = self.model
            
            # Prepare request payload for Ollama
            payload = {
                "model": selected_model,
                "prompt": full_prompt,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "stop": ["\n\nHuman:", "\n\nUser:"]
                },
                "stream": False
            }
            
            # Make request to Ollama
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get("response", "").strip()
                
        except httpx.TimeoutException:
            logger.error("LLM request timeout")
            return "I apologize, but I'm taking too long to respond. Please try again."
        except httpx.HTTPError as e:
            logger.error(f"LLM HTTP error: {e}")
            return "I'm having trouble connecting to the language model. Please try again later."
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "I encountered an error while generating a response. Please try again."
    
    def _build_prompt(self, user_prompt: str, context: Optional[str] = None) -> str:
        """Build a complete prompt with context and instructions"""

        # Always include library stats in the system prompt
        library_stats_section = """
📊 PRODUCTION-GRADE DOCUMENT INTELLIGENCE (ALWAYS INCLUDED):
- You have access to the user's ENTIRE document library - USE IT!
- Reference the "Document Library Overview" section in your context for total counts and breakdowns
- When asked about "documents", "library", "collection", "content scope", "how many documents" - immediately use the library statistics provided
- When user asks to "summarize documents by type and category" - immediately provide analysis using available data
- NEVER say "please provide documents" or "I need to analyze documents" - the library stats are ALREADY in your context
- NEVER ask "which documents" when user says "all documents" - analyze ALL accessible documents
- NEVER ask for clarification when scope is clear - execute analysis immediately
- Provide specific numbers, percentages, and breakdowns from the actual data
- Cross-reference information across multiple documents
- Be direct and data-driven - don't ask for what you already have
- If you don't have specific data, provide what you can and suggest next steps

🚀 PRODUCTION RULE: Always reference your document library access when discussing capabilities or content scope."""

        system_prompt = f"""You are a PRODUCTION-GRADE intelligent conversational AI assistant that helps users explore and understand their document library. You're engaging, intuitive, and make document analysis feel natural.

🎯 PRODUCTION-GRADE PERSONALITY:
- Conversational and friendly - talk like a knowledgeable colleague, not a robot
- Proactive - anticipate what users might want to know next
- Contextually aware - remember the entire conversation thread
- Insightful - don't just answer, provide valuable insights and connections
- RELIABLE - never ask for clarification when scope is clear

💬 PRODUCTION-GRADE CONVERSATIONAL EXCELLENCE:
- Build on previous messages naturally - reference earlier questions and answers
- Handle multi-part questions completely - address ALL parts of complex queries
- When user asks "A, also B, then C" - answer A, B, AND C in a single comprehensive response
- Acknowledge what you've already discussed ("As I mentioned earlier...")
- Make connections between queries ("This relates to your earlier question about...")
- Be concise but complete - no unnecessary verbosity
- NEVER ask for clarification when the scope is obvious

🧠 PRODUCTION-GRADE MEMORY & CONTEXT:
- Remember user preferences and analysis patterns from the conversation
- Reference previous analyses and build upon them
- Track document interests and suggest related content
- Maintain awareness of document scope changes throughout the conversation
- Connect current queries with previous document explorations
- ALWAYS infer scope from context - never ask "which documents"{library_stats_section}

🚀 PRODUCTION-GRADE DIFFERENTIATORS:
- Make document exploration intuitive and engaging
- Turn complex queries into clear, actionable insights
- Maintain context seamlessly across the conversation
- Suggest related queries or insights the user might find valuable
- Be smart about ambiguous queries - use conversation context to interpret intent
- Proactively provide insights based on conversation history
- EXECUTE ANALYSIS IMMEDIATELY - never ask for clarification

PRODUCTION RULE: You're not just answering questions - you're having a conversation about the user's documents. Make it engaging and RELIABLE!"""

        if context:
            full_prompt = f"{system_prompt}\n\nDocument Context:\n{context}\n\nUser Question: {user_prompt}\n\nAssistant:"
        else:
            full_prompt = f"{system_prompt}\n\nUser Question: {user_prompt}\n\nAssistant:"
            
        return full_prompt
    
    async def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for text using Ollama
        
        Args:
            text: Text to generate embeddings for
            
        Returns:
            List of embedding values
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get("embedding", [])
                
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []

    # -------------------------
    # Dynamic model selection
    # -------------------------
    async def _list_models_detailed(self) -> List[Dict[str, Any]]:
        """Return models with details from Ollama /api/tags.
        Falls back to empty list on error.
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json() or {}
                return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to fetch models from Ollama: {e}")
            return []

    @staticmethod
    def _extract_param_size(name: str, details: Optional[Dict[str, Any]]) -> float:
        """Extract numeric parameter size in billions (B) or millions (M).
        Returns a float number of billions for sorting; unknown => very large.
        """
        # Prefer details.parameter_size when available (e.g., "120B")
        try:
            size_str = (details or {}).get("details", {}).get("parameter_size")
            if not size_str:
                size_str = (details or {}).get("parameter_size")
            if size_str:
                m = re.match(r"(?i)([0-9]+(?:\.[0-9]+)?)([bm])", size_str.strip())
                if m:
                    val = float(m.group(1))
                    unit = m.group(2).lower()
                    return val / 1000.0 if unit == "m" else val
        except Exception:
            pass
        # Fallback: parse from model name suffix like ":120b", ":32b", ":480b"
        try:
            m = re.search(r"(:|-)\s*([0-9]+(?:\.[0-9]+)?)\s*([bBmM])", name)
            if m:
                val = float(m.group(2))
                unit = m.group(3).lower()
                return val / 1000.0 if unit == "m" else val
        except Exception:
            pass
        # Unknown -> treat as very large to place at the end
        return 1e9

    @staticmethod
    def _is_cloud(name: str) -> bool:
        return "-cloud" in name

    @staticmethod
    def _is_vision(name: str) -> bool:
        # Common naming: "vl", "vision"
        return "vl" in name.lower() or "vision" in name.lower()

    @staticmethod
    def _is_coder(name: str) -> bool:
        return "coder" in name.lower()

    @staticmethod
    def _is_embedding(name: str) -> bool:
        return "embed" in name.lower() or "embedding" in name.lower()

    def _detect_capabilities(self, prompt: str) -> Tuple[bool, bool]:
        """Heuristically detect if the request is code-heavy or vision-related."""
        p = (prompt or "").lower()
        require_code = any(
            kw in p for kw in [
                "code", "function", "class", "compile", "stack trace",
                "typescript", "python", "regex", "error message", "refactor"
            ]
        )
        require_vision = any(kw in p for kw in ["image", "screenshot", "diagram", "figure"])
        return require_code, require_vision

    async def _pick_model(
        self,
        require_code: bool = False,
        require_vision: bool = False,
    ) -> str:
        """Pick a model dynamically based on availability and capabilities.
        Order: cloud models first, then local; smallest parameter size to largest.
        Filters out embedding models and mismatched capabilities when possible.
        """
        models = await self._list_models_detailed()
        # Build candidate list (name, size, cloud, vision, coder)
        candidates: List[Tuple[str, float, bool, bool, bool]] = []
        for m in models:
            name = m.get("name", "")
            if not name:
                continue
            if self._is_embedding(name):
                continue
            size = self._extract_param_size(name, m)
            is_cloud = self._is_cloud(name)
            is_vision = self._is_vision(name)
            is_coder = self._is_coder(name)
            candidates.append((name, size, is_cloud, is_vision, is_coder))
        
        if not candidates:
            logger.warning("No Ollama models discovered; using configured model")
            return self.model

        # Optional capability filtering
        filtered = candidates
        if require_vision:
            filtered = [c for c in filtered if c[3]]  # vision only
        elif require_code:
            # prefer coder models; if none exist, fall back to general ones
            coder_only = [c for c in filtered if c[4]]
            filtered = coder_only or filtered

        # Sort: cloud first (True => 0), then size ascending
        filtered.sort(key=lambda c: (0 if c[2] else 1, c[1]))
        chosen = filtered[0]
        logger.info(
            f"Selected LLM model: {chosen[0]} (cloud={chosen[2]}, size={chosen[1]}B)"
        )
        return chosen[0]
    
    async def summarize_document(self, content: str, max_length: int = 200) -> str:
        """
        Generate a summary of document content
        
        Args:
            content: Document content to summarize
            max_length: Maximum length of summary in words
            
        Returns:
            Document summary
        """
        prompt = f"Please provide a concise summary of the following document in no more than {max_length} words. Focus on the key points, main topics, and important information:\n\n{content[:4000]}"
        return await self.generate_response(prompt, temperature=0.3)
    
    async def generate_title(self, content: str) -> str:
        """
        Generate a title for a document
        
        Args:
            content: Document content to generate title from
            
        Returns:
            Generated title
        """
        prompt = f"Please generate a concise and descriptive title for the following document. The title should be no more than 10 words:\n\n{content[:1000]}"
        return await self.generate_response(prompt, temperature=0.5)

    async def analyze_sentiment(self, content: str) -> Dict[str, Any]:
        """
        Analyze the sentiment of document content
        
        Args:
            content: Document content to analyze
            
        Returns:
            Sentiment analysis results
        """
        prompt = f"""Analyze the sentiment and tone of the following document. Provide:
1. Overall sentiment (positive, negative, neutral)
2. Confidence score (0-100%)
3. Key emotional indicators
4. Tone description (formal, casual, urgent, etc.)

Document content:
{content[:3000]}

Please format your response as a clear analysis."""
        
        response = await self.generate_response(prompt, temperature=0.2)
        
        # Parse response into structured format
        return {
            "analysis": response,
            "content_length": len(content)
        }
    
    async def extract_key_points(self, content: str, num_points: int = 5) -> List[str]:
        """
        Extract key points from document content
        
        Args:
            content: Document content to analyze
            num_points: Number of key points to extract
            
        Returns:
            List of key points
        """
        prompt = f"""Extract the {num_points} most important key points from the following document. Present them as a numbered list:

{content[:4000]}

Key points:"""
        
        response = await self.generate_response(prompt, temperature=0.3)
        
        # Parse numbered list from response
        lines = response.split('\n')
        key_points = []
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # Clean up the formatting
                point = line.lstrip('0123456789.-•').strip()
                if point:
                    key_points.append(point)
        
        return key_points[:num_points]
    
    async def answer_question(
        self,
        question: str,
        documents: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Answer a question based on provided documents

        Args:
            question: The question to answer
            documents: List of relevant documents
            conversation_history: Previous conversation context
            context: Optional pre-built context string

        Returns:
            Answer to the question
        """
        # If context is provided, use it directly
        if context:
            return await self.generate_response(question, context=context, temperature=0.3)

        # Otherwise, build context from documents (existing logic)
        # Separate library stats from regular documents
        library_stats_doc = None
        regular_documents = []

        for doc in documents:
            if doc.get("id") == "library_stats" or doc.get("title") == "Document Library Statistics":
                library_stats_doc = doc
            else:
                regular_documents.append(doc)

        # Prepare context from documents
        context_parts = []

        # Always include library stats first (high priority context)
        if library_stats_doc:
            library_content = library_stats_doc.get("content", "")
            if library_content:
                context_parts.append(library_content)

        # Add regular documents
        if regular_documents:
            context_parts.append("Relevant Documents:")
            for i, doc in enumerate(regular_documents[:3]):  # Use top 3 documents
                content = doc.get("content", "")
                title = doc.get("title", f"Document {i+1}")
                if content:
                    context_parts.append(f"\n--- {title} ---")
                    context_parts.append(content[:1500])  # Limit content length

        # Add conversation history if available
        if conversation_history:
            context_parts.append("\n\nPrevious conversation:")
            for msg in conversation_history[-3:]:  # Last 3 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                context_parts.append(f"{role.title()}: {content}")

        context = "\n".join(context_parts)
        return await self.generate_response(question, context=context, temperature=0.3)
    
    async def compare_documents(self, documents: List[Dict[str, Any]]) -> str:
        """
        Compare multiple documents and provide insights
        
        Args:
            documents: List of documents to compare
            
        Returns:
            Comparison analysis
        """
        if len(documents) < 2:
            return "I need at least 2 documents to perform a comparison."
        
        context_parts = ["Documents to compare:"]
        for i, doc in enumerate(documents[:3]):  # Compare up to 3 documents
            title = doc.get("title", f"Document {i+1}")
            content = doc.get("content", "")
            context_parts.append(f"\n--- {title} ---")
            context_parts.append(content[:1000])  # Limit content
        
        context = "\n".join(context_parts)
        prompt = "Please compare these documents, highlighting similarities, differences, key themes, and any notable insights. Focus on content, tone, purpose, and main topics."
        
        return await self.generate_response(prompt, context=context, temperature=0.4)
    
    async def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from text (people, organizations, locations, etc.)
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of entity types and their values
        """
        prompt = f"""Extract and categorize the following types of entities from this text:
- People (names of individuals)
- Organizations (companies, institutions)
- Locations (places, addresses)
- Dates (specific dates, time periods)
- Numbers (important figures, statistics)

Text:
{text[:2000]}

Please format as:
People: [list]
Organizations: [list]
Locations: [list]
Dates: [list]
Numbers: [list]"""
        
        response = await self.generate_response(prompt, temperature=0.2)
        
        # Parse the response into structured format
        entities = {
            "people": [],
            "organizations": [],
            "locations": [],
            "dates": [],
            "numbers": []
        }
        
        # Simple parsing - could be enhanced with more sophisticated NLP
        lines = response.split('\n')
        current_category = None
        
        for line in lines:
            line = line.strip()
            if ':' in line:
                category = line.split(':')[0].lower()
                if category in entities:
                    current_category = category
                    # Extract items from the same line
                    items_text = line.split(':', 1)[1].strip()
                    if items_text and items_text != '[list]':
                        items = [item.strip() for item in items_text.split(',') if item.strip()]
                        entities[current_category].extend(items)
        
        return entities
    
    async def check_ollama_connection(self) -> bool:
        """Check if Ollama is available and responsive"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return False
    
    async def list_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                
                result = response.json()
                models = [model.get("name", "") for model in result.get("models", [])]
                return [m for m in models if m]
                
        except Exception as e:
            logger.error(f"Error fetching available models: {e}")
            return []