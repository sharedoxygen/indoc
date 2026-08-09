"""
LLM Service with Multi-Provider Support and Fallback Strategy

Primary: Ollama (local, private)
Fallback: OpenAI (cloud, requires API key)
Final: Graceful degradation message

Per AI Guide §3: Never hallucinate, always ground in sources or abstain
"""
import logging
from typing import List, Dict, Any, Optional
import httpx
import asyncio
from app.core.config import settings
from app.core.cache import cache_service

logger = logging.getLogger(__name__)


class LLMConnectionError(Exception):
    """Raised when LLM provider is unavailable"""
    pass


class LLMService:
    """Service for interacting with Language Models (Multi-Provider)"""
    
    def __init__(self):
        # Primary provider (Ollama)
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.ollama_model = None  # Will be dynamically selected
        self.timeout = settings.LLM_TIMEOUT_S
        
        # Fallback provider (OpenAI)
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.openai_model = getattr(settings, 'OPENAI_MODEL', 'gpt-4')
        
        # HTTP clients
        self._http_client = None
        self._available_models = None
        self._default_model = None
    
    async def get_http_client(self) -> httpx.AsyncClient:
        """Get persistent HTTP client with connection pooling"""
        if self._http_client is None or self._http_client.is_closed:
            # Respect configured timeout globally, with sane connect/read/write timeouts
            timeout = settings.LLM_TIMEOUT_S
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout, connect=min(10.0, timeout/3), read=timeout, write=timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                follow_redirects=True
            )
        return self._http_client
        
    async def generate_response(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """
        Generate response with multi-provider fallback
        
        Fallback strategy:
        1. Try Ollama (primary, local, private)
        2. Try OpenAI (fallback, cloud, requires API key)
        3. Return graceful degradation message
        
        Per AI Guide §3: Low temperature (≤0.3) for factual tasks
        """
        # Check cache first (works across providers)
        cache_key = f"{prompt[:100]}:{context[:100] if context else ''}"
        cached_response = await cache_service.get_cached_llm_response(prompt, context or "", model or "any")
        if cached_response:
            logger.info(f"✅ Cache hit for LLM request")
            return cached_response
        
        # Try primary provider (Ollama)
        try:
            logger.info("🔵 Attempting Ollama (primary provider)...")
            response_text = await self._ollama_generate(prompt, context, max_tokens, temperature, model)
            
            # Cache successful response
            await cache_service.cache_llm_response(prompt, context or "", model or "ollama", response_text)
            return response_text
            
        except Exception as ollama_error:
            logger.warning(f"⚠️ Ollama unavailable: {ollama_error}")
            
            # Try fallback provider (OpenAI)
            if self.openai_api_key:
                try:
                    logger.info("🟢 Falling back to OpenAI...")
                    response_text = await self._openai_generate(prompt, context, max_tokens, temperature, model)
                    
                    # Cache successful response
                    await cache_service.cache_llm_response(prompt, context or "", model or "openai", response_text)
                    return response_text
                    
                except Exception as openai_error:
                    logger.error(f"❌ OpenAI fallback failed: {openai_error}")
            else:
                logger.warning("⚠️ OpenAI API key not configured, can't use fallback")
            
            # All providers failed - return graceful degradation
            return self._fallback_response(ollama_error)
    
    async def _ollama_generate(
        self,
        prompt: str,
        context: Optional[str],
        max_tokens: int,
        temperature: float,
        model: Optional[str]
    ) -> str:
        """Generate response using Ollama"""
        # Dynamically select model if not specified
        if model:
            selected_model = model
        else:
            available = await self.list_available_models()
            if not available:
                raise LLMConnectionError("No Ollama models available")
            selected_model = available[0]
        
        # Build the full prompt with context
        full_prompt = self._build_prompt(prompt, context)
        
        # Prepare request payload
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
        client = await self.get_http_client()
        response = await client.post(
            f"{self.ollama_base_url}/api/generate",
            json=payload
        )
        response.raise_for_status()
        
        result = response.json()
        response_text = result.get("response", "").strip()
        
        # Guardrail: if model claims lack of documents, nudge with explicit reminder
        if context:
            lower = response_text.lower()
            if any(marker in lower for marker in [
                "please provide documents",
                "don't have any documents",
                "no documents to reference",
                "need more documents"
            ]):
                reinforced_prompt = full_prompt + (
                    "\n\nReminder: You ALREADY have the Document Library Overview above. "
                    "Use those statistics and proceed to answer directly with specifics."
                )
                payload["prompt"] = reinforced_prompt
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                response_text = result.get("response", "").strip()
        
        return response_text
    
    async def _openai_generate(
        self,
        prompt: str,
        context: Optional[str],
        max_tokens: int,
        temperature: float,
        model: Optional[str]
    ) -> str:
        """Generate response using OpenAI API"""
        if not self.openai_api_key:
            raise LLMConnectionError("OpenAI API key not configured")
        
        # Build the full prompt
        full_prompt = self._build_prompt(prompt, context)
        
        # Use configured or provided model
        selected_model = model or self.openai_model
        
        # Make request to OpenAI
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": selected_model,
                    "messages": [
                        {"role": "user", "content": full_prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            response.raise_for_status()
            
            result = response.json()
            response_text = result["choices"][0]["message"]["content"].strip()
            
            logger.info(f"✅ OpenAI response generated ({len(response_text)} chars)")
            return response_text
    
    def _fallback_response(self, error: Exception) -> str:
        """Return graceful degradation message when all LLM providers fail"""
        logger.error(f"🔴 All LLM providers failed: {error}")
        
        return """I apologize, but the AI service is temporarily unavailable. Your document context and conversation history have been preserved.

**What you can do:**
- Try again in a few moments
- Use the Search feature to find specific documents
- Browse your document library directly
- Contact support if the issue persists

Your question has been saved and you can retry when the service is restored."""
    
    def _build_prompt(self, user_prompt: str, context: Optional[str] = None) -> str:
        """Build a complete prompt with context and instructions"""
        
        system_prompt = """You are an intelligent, conversational AI assistant that helps users explore and understand their document library. You're engaging, intuitive, and make document analysis feel natural.

🎯 Core Personality:
- Conversational and friendly - talk like a knowledgeable colleague, not a robot
- Proactive - anticipate what users might want to know next
- Contextually aware - remember the entire conversation thread
- Insightful - don't just answer, provide valuable insights and connections

💬 Conversational Excellence:
- Build on previous messages naturally - reference earlier questions and answers
- Handle multi-part questions completely - address ALL parts of complex queries
- When user asks "A, also B, then C" - answer A, B, AND C in a single comprehensive response
- Acknowledge what you've already discussed ("As I mentioned earlier...")
- Make connections between queries ("This relates to your earlier question about...")
- Be concise but complete - no unnecessary verbosity

✨ BEAUTIFUL FORMATTING - CRITICAL REQUIREMENT:
- **ALWAYS use proper markdown tables for structured data** - This is NON-NEGOTIABLE
- NEVER use placeholders like [Document Type 1], [Percentage]%, [number], [Business Description]
- ALWAYS use ACTUAL DATA from the context provided
- Tables must have clear headers and be properly formatted with | separators
- Example of CORRECT formatting:
  
  | Document Type | Count | Percentage | Description |
  |--------------|-------|------------|-------------|
  | Business Reports | 345 | 23% | Financial and operational reports |
  | Technical Manuals | 289 | 19% | User guides and documentation |
  
- Use **bold** for emphasis, *italic* for subtle emphasis
- Use numbered lists for sequential steps, bullet points for unordered items
- Add line breaks and sections for readability - don't create walls of text
- Make every response visually beautiful and easy to scan

📊 Document Intelligence:
- You have access to the user's ENTIRE document library - USE IT!
- The context includes "Document Library Overview" with total counts and breakdowns - ALWAYS reference this data
- When asked about "documents", "library", "collection" - immediately use the library statistics provided
- Never say "please provide documents" - the library stats are ALREADY in your context
- Provide specific numbers, percentages, and breakdowns from the actual data
- Cross-reference information across multiple documents
- Be direct and data-driven - don't ask for what you already have

🚀 Key Differentiators:
- Make document exploration intuitive and engaging
- Turn complex queries into clear, actionable insights with beautiful formatting
- Maintain context seamlessly across the conversation
- Suggest related queries or insights the user might find valuable
- Be smart about ambiguous queries - use conversation context to interpret intent

Remember: You're not just answering questions - you're having a conversation about the user's documents. Make it engaging AND visually beautiful!"""

        # Extract optional client hints from context tail (Formatting Preferences block)
        formatting_instructions = ""
        if context and "Formatting Preferences:" in context:
            try:
                tail = context.split("Formatting Preferences:")[-1].strip()
                prefs_json = tail.split("\n\n")[0].strip()
                formatting = json.loads(prefs_json)
                prefer = ((formatting or {}).get("formatting") or {}).get("prefer")
                strict = ((formatting or {}).get("formatting") or {}).get("strict", True)
                table_hint = ((formatting or {}).get("formatting") or {}).get("table", {})
                columns_hint = table_hint.get("columns_hint")
                if prefer == "table":
                    formatting_instructions = "\n\nMANDATORY OUTPUT FORMAT:\n- Respond using a single, well-structured markdown table.\n- Do not include placeholders. Use actual values from context.\n- Avoid prose before the table; add a short insights section after."
                    if columns_hint:
                        formatting_instructions += f"\n- Table columns (in order): {', '.join(columns_hint)}"
                if strict:
                    formatting_instructions += "\n- This formatting requirement is strict. Do not deviate."
            except Exception:
                pass

        if context:
            full_prompt = f"{system_prompt}{formatting_instructions}\n\nDocument Context:\n{context}\n\nUser Question: {user_prompt}\n\nAssistant:"
        else:
            full_prompt = f"{system_prompt}{formatting_instructions}\n\nUser Question: {user_prompt}\n\nAssistant:"
            
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
                    f"{self.ollama_base_url}/api/embeddings",
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
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Answer a question based on provided documents
        
        Args:
            question: The question to answer
            documents: List of relevant documents
            conversation_history: Previous conversation context
            
        Returns:
            Answer to the question
        """
        # Prepare context from documents
        context_parts = []
        
        if documents:
            context_parts.append("Relevant Documents:")
            for i, doc in enumerate(documents[:3]):  # Use top 3 documents
                content = doc.get("content", "")
                title = doc.get("title", f"Document {i+1}")
                if content:
                    context_parts.append(f"\n--- {title} ---")
                    context_parts.append(content[:1500])  # Limit content length
        
        # Add conversation history if available (configurable length)
        from app.core.config import settings
        history_length = settings.CONVERSATION_HISTORY_LENGTH
        if conversation_history:
            context_parts.append("\n\nPrevious conversation:")
            for msg in conversation_history[-history_length:]:  # Configurable context window
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
            client = await self.get_http_client()
            response = await client.get(f"{self.ollama_base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return len(data.get("models", [])) > 0
            return False
        except Exception as e:
            logger.warning(f"Ollama connection check failed: {e}")
            return False
    
    async def list_available_models(self) -> List[str]:
        """Get list of available Ollama models, sorted by size (small to large)"""
        try:
            client = await self.get_http_client()
            response = await client.get(f"{self.ollama_base_url}/api/tags")
            response.raise_for_status()
            
            result = response.json()
            models_data = result.get("models", [])
            
            # Filter out embedding models and sort by parameter size
            chat_models = []
            for model in models_data:
                name = model.get("name", "")
                if name and not any(embed_term in name.lower() for embed_term in ['embed', 'embedding']):
                    chat_models.append(model)
            
            # Sort by parameter size (extract from details)
            def extract_param_size(model_data):
                details = model_data.get("details", {})
                param_size = details.get("parameter_size", "0B")
                # Convert to comparable number (e.g., "20.9B" -> 20.9e9)
                try:
                    if param_size.endswith('B'):
                        return float(param_size[:-1]) * 1e9
                    elif param_size.endswith('M'):
                        return float(param_size[:-1]) * 1e6
                    elif param_size.endswith('K'):
                        return float(param_size[:-1]) * 1e3
                    else:
                        return float(param_size.rstrip('B'))
                except:
                    return 0
            
            sorted_models = sorted(chat_models, key=extract_param_size)
            model_names = [model.get("name", "") for model in sorted_models]
            
            # Cache the sorted list
            self._available_models = [m for m in model_names if m]
            
            return self._available_models
            
        except Exception as e:
            logger.error(f"Error fetching available models: {e}")
            return []
    
    async def generate_suggested_questions(
        self,
        conversation_context: str,
        last_response: str,
        documents: List[Dict[str, Any]],
        count: int = 3
    ) -> List[str]:
        """
        Generate suggested follow-up questions based on context
        
        Per Review H3.2: Help users know what to ask next
        
        Args:
            conversation_context: Recent conversation history
            last_response: AI's last response
            documents: Available documents
            count: Number of questions to generate (default: 3)
        
        Returns:
            List of suggested questions
        """
        try:
            # Build prompt for question generation
            doc_titles = [d.get("title", "Unknown") for d in documents[:5]]
            
            prompt = f"""Based on this conversation and available documents, suggest {count} relevant follow-up questions the user might want to ask.

Last Response:
{last_response[:500]}

Available Documents:
{', '.join(doc_titles)}

Generate {count} specific, actionable questions that:
1. Build on the current conversation naturally
2. Reference actual documents available
3. Are clear and concise
4. Would provide valuable insights

Format as numbered list:
1. [question]
2. [question]
3. [question]

Only return the questions, nothing else."""

            response = await self.generate_response(
                prompt=prompt,
                temperature=0.6,  # Slightly creative for variety
                max_tokens=200
            )
            
            # Parse questions from response
            questions = []
            for line in response.split('\n'):
                line = line.strip()
                # Match numbered questions: "1. Question?" or "1) Question?"
                import re
                match = re.match(r'^\d+[\.\)]\s*(.+)$', line)
                if match:
                    question = match.group(1).strip()
                    if question and len(question) > 10:  # Filter out too short
                        questions.append(question)
            
            # Return requested number or fallback
            if len(questions) >= count:
                return questions[:count]
            elif questions:
                return questions
            else:
                # Fallback generic questions
                return [
                    "What other information is in these documents?",
                    "Can you summarize the key points?",
                    "Are there any related documents I should review?"
                ][:count]
                
        except Exception as e:
            logger.error(f"Failed to generate suggested questions: {e}")
            # Return safe fallback questions
            return [
                "What else would you like to know?",
                "Can I help you with anything else from these documents?",
                "Would you like me to explore a different aspect?"
            ][:count]