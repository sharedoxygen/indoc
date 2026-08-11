"""
Agent tools for the inDoc autonomous research agent.

Each tool is a scope-aware capability the agent can choose to invoke while
working toward a goal. Every tool that touches documents enforces the same
RBAC/ABAC scope as the rest of the platform - the agent can only ever see or
read documents the requesting user is authorized to access. This is what makes
autonomous, multi-step reasoning safe to run over regulated document libraries.
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.core.document_scope import get_effective_document_ids
from app.models.document import Document
from app.models.user import User
from app.services.llm_service import LLMService
from app.services.search_service import SearchService

logger = logging.getLogger(__name__)


class ToolError(Exception):
    """Raised when a tool receives invalid input it cannot recover from."""


class AgentTools:
    """
    Registry of tools available to the agent, bound to a request's db session
    and authenticated user so every call is scope-enforced.
    """

    def __init__(self, db, user: User, llm_service: Optional[LLMService] = None):
        self.db = db
        self.user = user
        self.search_service = SearchService(db)
        # Some tools (compare / summarize) reason over document content with
        # the LLM. Reuse the agent's LLM so provider/fallback config is shared.
        self.llm = llm_service or LLMService()

    # --- Tool metadata advertised to the LLM planner ---------------------

    def describe(self) -> List[Dict[str, Any]]:
        """Return the tool catalog the planner sees each step."""
        return [
            {
                "name": "list_documents",
                "description": (
                    "Quick catalog peek (capped sample of ids/titles in scope). "
                    "Optional survey only — NEVER treat the list as items to "
                    "summarize one-by-one. Prefer search_documents for goals."
                ),
                "input_schema": {},
            },
            {
                "name": "search_documents",
                "description": (
                    "PRIMARY tool for corpus-scale goals. Hybrid keyword + "
                    "semantic search returns the most relevant docs with "
                    "snippets. Use targeted queries (e.g. liability, indemnity, "
                    "termination) instead of reading every file."
                ),
                "input_schema": {
                    "query": "string (required) - what to search for",
                    "limit": "integer (optional, default 8, max 15)",
                },
            },
            {
                "name": "read_document",
                "description": (
                    "Read full text of ONE high-value document after search. "
                    "Do not call this in a loop across the corpus — capped per run."
                ),
                "input_schema": {
                    "document_id": "string (required) - the document uuid",
                },
            },
            {
                "name": "summarize_document",
                "description": (
                    "Summarize ONE top search hit when you need the gist. "
                    "Forbidden as a corpus walk — never summarize every listed "
                    "document. Capped per run; prefer search snippets."
                ),
                "input_schema": {
                    "document_id": "string (required) - the document uuid",
                },
            },
            {
                "name": "compare_documents",
                "description": (
                    "Compare two or more documents by their ids and get back "
                    "their key similarities and differences. Use this when the "
                    "goal is about what changed or how documents differ."
                ),
                "input_schema": {
                    "document_ids": "array of strings (required, min 2) - document uuids",
                },
            },
            {
                "name": "finish",
                "description": (
                    "Provide the final answer to the user's goal, grounded in "
                    "what you gathered. Use this when you have enough evidence. "
                    "The answer must be Markdown: short intro, categorized "
                    "bullet/numbered list with bold labels, cite document "
                    "titles and ids, one-line takeaway — not a single paragraph."
                ),
                "input_schema": {
                    "answer": (
                        "string (required) - Markdown final answer with "
                        "categories, citations, and a short takeaway"
                    ),
                },
            },
        ]

    def tool_names(self) -> List[str]:
        return [t["name"] for t in self.describe()]

    # --- Tool dispatch ----------------------------------------------------

    async def execute(self, action: str, action_input: Dict[str, Any]) -> str:
        """Execute a tool by name and return a text observation for the agent."""
        action_input = action_input or {}
        if action == "list_documents":
            return await self._list_documents()
        if action == "search_documents":
            return await self._search_documents(action_input)
        if action == "read_document":
            return await self._read_document(action_input)
        if action == "summarize_document":
            return await self._summarize_document(action_input)
        if action == "compare_documents":
            return await self._compare_documents(action_input)
        raise ToolError(
            f"Unknown tool '{action}'. Available tools: {', '.join(self.tool_names())}"
        )

    async def _scoped_document_ids(self) -> Optional[set]:
        """Resolve the set of internal document ids this user may access."""
        if not self.user or not hasattr(self.db, "execute"):
            return None
        return await get_effective_document_ids(self.db, self.user)

    async def _list_documents(self) -> str:
        scoped_ids = await self._scoped_document_ids()
        if scoped_ids is not None and not scoped_ids:
            return "No documents are accessible to you."

        from sqlalchemy import func

        count_q = select(func.count()).select_from(Document)
        if scoped_ids is not None:
            count_q = count_q.where(Document.id.in_(scoped_ids))
        total = int((await self.db.execute(count_q)).scalar() or 0)

        query = select(Document.uuid, Document.title, Document.filename, Document.file_type)
        if scoped_ids is not None:
            query = query.where(Document.id.in_(scoped_ids))
        query = query.limit(20)

        rows = (await self.db.execute(query)).all()
        if not rows:
            return "No documents are accessible to you."

        lines = [
            f"- id={row[0]} | title={row[1] or row[2]} | type={row[3]}"
            for row in rows
        ]
        return (
            f"{total} document(s) in scope (showing {len(rows)} sample titles only).\n"
            "Do NOT summarize or read each document. Use search_documents with "
            "goal-focused queries, then deep-dive at most 1–2 top hits, then finish.\n"
            + "\n".join(lines)
        )

    async def _search_documents(self, action_input: Dict[str, Any]) -> str:
        query = action_input.get("query")
        if not query or not str(query).strip():
            raise ToolError("search_documents requires a non-empty 'query'.")
        limit = int(action_input.get("limit", 8) or 8)
        limit = max(1, min(limit, 15))

        results = await self.search_service.hybrid_search(
            query=str(query), limit=limit, user=self.user
        )
        if not results:
            return f"No documents matched the query: {query!r}."

        lines = []
        for r in results:
            title = (r.metadata or {}).get("title") or "Untitled"
            snippet = (r.content or "").strip().replace("\n", " ")
            if len(snippet) > 300:
                snippet = snippet[:300] + "..."
            lines.append(
                f"- id={r.document_id} | title={title} | score={r.score:.3f}\n  {snippet}"
            )
        return f"Top {len(results)} result(s) for {query!r}:\n" + "\n".join(lines)

    async def _get_scoped_document(self, document_id: str) -> Optional[Document]:
        """Fetch a document only if it is within the user's accessible scope."""
        scoped_ids = await self._scoped_document_ids()
        doc_query = select(Document).where(Document.uuid == str(document_id).strip())
        if scoped_ids is not None:
            doc_query = doc_query.where(Document.id.in_(scoped_ids))
        return (await self.db.execute(doc_query)).scalar_one_or_none()

    async def _read_document(self, action_input: Dict[str, Any]) -> str:
        document_id = action_input.get("document_id")
        if not document_id or not str(document_id).strip():
            raise ToolError("read_document requires a 'document_id'.")

        doc = await self._get_scoped_document(document_id)
        if doc is None:
            return (
                f"Document {document_id} is not available to you (either it does "
                "not exist or you lack access). Do not assume its contents."
            )

        content = (doc.full_text or doc.description or "").strip()
        if not content:
            return f"Document '{doc.title or doc.filename}' has no extractable text content."
        if len(content) > 4000:
            content = content[:4000] + "... (truncated)"
        return f"Content of '{doc.title or doc.filename}':\n{content}"

    async def _summarize_document(self, action_input: Dict[str, Any]) -> str:
        document_id = action_input.get("document_id")
        if not document_id or not str(document_id).strip():
            raise ToolError("summarize_document requires a 'document_id'.")

        doc = await self._get_scoped_document(document_id)
        if doc is None:
            return (
                f"Document {document_id} is not available to you. "
                "Do not assume its contents."
            )
        content = (doc.full_text or doc.description or "").strip()
        if not content:
            return f"Document '{doc.title or doc.filename}' has no text to summarize."

        prompt = (
            "Summarize the following document in 3-4 sentences, capturing its "
            "main points and any figures. Be faithful to the text; do not add "
            f"information.\n\nDocument: {doc.title or doc.filename}\n\n{content[:6000]}"
        )
        summary = await self.llm.generate_response(prompt=prompt, max_tokens=400, temperature=0.2)
        return f"Summary of '{doc.title or doc.filename}':\n{summary.strip()}"

    async def _compare_documents(self, action_input: Dict[str, Any]) -> str:
        raw_ids = action_input.get("document_ids") or []
        if isinstance(raw_ids, str):
            raw_ids = [raw_ids]
        ids = [str(d).strip() for d in raw_ids if str(d).strip()]
        if len(ids) < 2:
            raise ToolError("compare_documents requires at least 2 document ids.")

        fetched = []
        skipped = []
        for doc_id in ids[:5]:  # bound the work
            doc = await self._get_scoped_document(doc_id)
            if doc is None:
                skipped.append(doc_id)
                continue
            content = (doc.full_text or doc.description or "").strip()
            fetched.append((doc.title or doc.filename, content[:3000]))

        if len(fetched) < 2:
            return (
                "Could not access at least two of the requested documents "
                f"(skipped: {', '.join(skipped) or 'none'}). Cannot compare."
            )

        blocks = "\n\n".join(
            f"--- Document {i + 1}: {title} ---\n{content}"
            for i, (title, content) in enumerate(fetched)
        )
        prompt = (
            "Compare the following documents. List their key similarities and "
            "the most important differences, referencing each by title. Base "
            f"everything only on the text provided.\n\n{blocks}"
        )
        comparison = await self.llm.generate_response(prompt=prompt, max_tokens=700, temperature=0.2)
        note = f" (skipped inaccessible: {', '.join(skipped)})" if skipped else ""
        return f"Comparison of {len(fetched)} documents{note}:\n{comparison.strip()}"
