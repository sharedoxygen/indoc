"""
Fixtures for the inDoc MCP server tests.

Self-contained (in-memory SQLite, Elasticsearch/Qdrant disabled so search
falls back to scoped DB keyword search) so they run in the indoc-mcp image:

    docker compose run --rm indoc-mcp pytest -o addopts="" \
        --confcutdir=tests/mcp_server tests/mcp_server
"""

from dataclasses import dataclass
from typing import AsyncGenerator, AsyncIterator, Dict

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registers every mapper on Base.metadata)
from app.core.security import get_password_hash
from app.mcp_server.auth import mint_mcp_token
from app.models.base import Base
from app.models.classification import DocumentClassification
from app.models.document import Document
from app.models.user import User, UserRole

from .helpers import VENDOR_CONTRACT_TEXT, running_server


@dataclass
class DemoWorld:
    manager: User
    analyst: User
    inactive: User
    finance_doc_ids: Dict[str, str]
    general_doc_ids: Dict[str, str]
    tokens: Dict[str, str]


@pytest.fixture(autouse=True)
def no_search_engines(monkeypatch):
    import app.services.search.elasticsearch_service as es_module
    import app.services.search.qdrant_service as qdrant_module

    monkeypatch.setattr(es_module, "get_elasticsearch_service", lambda: None)
    monkeypatch.setattr(qdrant_module, "get_qdrant_service", lambda: None)


@pytest.fixture
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


def _user(email: str, role: UserRole, **extra) -> User:
    return User(
        email=email,
        username=email.split("@")[0],
        full_name=email.split("@")[0],
        hashed_password=get_password_hash("not-used-in-tests"),
        role=role,
        is_active=extra.pop("is_active", True),
        is_verified=True,
        **extra,
    )


def _document(
    title: str, text: str, owner: User, classification: DocumentClassification
) -> Document:
    return Document(
        filename=f"{title.lower().replace(' ', '_')}.txt",
        file_type="txt",
        file_size=len(text),
        file_hash=f"mcp-test-{title}",
        storage_path=f"/tmp/{title}.txt",
        status="indexed",
        title=title,
        full_text=text,
        classification=classification,
        uploaded_by=owner.id,
    )


@pytest.fixture
async def world(session_factory) -> DemoWorld:
    async with session_factory() as db:
        manager = _user(
            "manager.test@example.com", UserRole.MANAGER, department="Finance"
        )
        inactive = _user("inactive.test@example.com", UserRole.MANAGER, is_active=False)
        db.add_all([manager, inactive])
        await db.flush()
        analyst = _user(
            "analyst.test@example.com", UserRole.ANALYST, manager_id=manager.id
        )
        db.add(analyst)
        await db.flush()

        finance = {
            "vendor_contract": _document(
                "Halvorsen Freight MSA",
                VENDOR_CONTRACT_TEXT,
                manager,
                DocumentClassification.RESTRICTED,
            ),
            "budget": _document(
                "Q3 Budget Variance",
                "Operating expenses exceeded plan by four percent.",
                manager,
                DocumentClassification.RESTRICTED,
            ),
        }
        general = {
            "travel": _document(
                "Travel Policy",
                "Book economy fares at least fourteen days ahead.",
                analyst,
                DocumentClassification.INTERNAL,
            ),
            "it_policy": _document(
                "IT Acceptable Use",
                "Report lost laptops to the service desk within one hour.",
                analyst,
                DocumentClassification.INTERNAL,
            ),
        }
        db.add_all([*finance.values(), *general.values()])
        await db.commit()

        return DemoWorld(
            manager=manager,
            analyst=analyst,
            inactive=inactive,
            finance_doc_ids={key: str(doc.uuid) for key, doc in finance.items()},
            general_doc_ids={key: str(doc.uuid) for key, doc in general.items()},
            tokens={
                "manager": mint_mcp_token(manager, 30),
                "analyst": mint_mcp_token(analyst, 30),
                "inactive": mint_mcp_token(inactive, 30),
            },
        )


@pytest.fixture
async def mcp_url(session_factory, world) -> AsyncIterator[str]:
    async with running_server(session_factory) as url:
        yield url
