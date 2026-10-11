#!/usr/bin/env python3
"""
Seed the synthetic two-user dataset for the Gemini ADK + MCP connector demo.

Idempotent: re-running updates the same users and documents in place and
re-indexes them in Elasticsearch and Qdrant.

    conda run -n indoc python tools/seed_mcp_demo.py           # seed + index
    conda run -n indoc python tools/seed_mcp_demo.py --purge   # remove demo data

Access model (inDoc RBAC/ABAC, unchanged):
  manager.demo@example.com  Manager  owns 3 RESTRICTED finance documents and,
                                     as the analyst's manager, also sees theirs
  analyst.demo@example.com  Analyst  reports to the manager; sees only their
                                     own 3 INTERNAL documents

The manager and analyst passwords are random and unrecorded: the agent uses
MCP tokens. gemini@indoc.local / GeminiDemo123! is the human login for this
corpus. Demo documents are visibility=grant, so they stay out of the personal
library unless the caller owns them or holds a read grant. gemini holds a
read grant on every demo document. --purge removes the documents and their
index entries and deactivates the users; their audit rows are retained.
"""
import argparse
import asyncio
import hashlib
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.document_scope import GRANT_VISIBILITY  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.db.session import AsyncSessionLocal, async_engine  # noqa: E402
from app.models.classification import DocumentClassification  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.models.document_permission import DocumentPermission  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.services.search.elasticsearch_service import ElasticsearchService  # noqa: E402
from app.services.search.qdrant_service import QdrantService  # noqa: E402
from app.services.search_service import SearchService  # noqa: E402

DOCUMENT_SET_ID = "mcp-demo"
MANAGER_EMAIL = "manager.demo@example.com"
ANALYST_EMAIL = "analyst.demo@example.com"
GEMINI_EMAIL = "gemini@indoc.local"
GEMINI_USERNAME = "gemini"
GEMINI_PASSWORD = "GeminiDemo123!"


@dataclass(frozen=True)
class DemoDoc:
    filename: str
    title: str
    owner: str
    classification: DocumentClassification
    text: str


DEMO_DOCS: List[DemoDoc] = [
    DemoDoc(
        filename="halvorsen_freight_msa.txt",
        title="Master Services Agreement - Halvorsen Freight",
        owner=MANAGER_EMAIL,
        classification=DocumentClassification.RESTRICTED,
        text=(
            "MASTER SERVICES AGREEMENT between Acme Corp (Customer) and Halvorsen Freight AS "
            "(Vendor), effective 1 February 2026, for regional freight and warehousing services.\n"
            "1. Term. Three (3) years from the effective date.\n"
            "2. Fees. Minimum annual commitment of USD 1,200,000, invoiced monthly, net 45.\n"
            "9. Termination.\n"
            "9.1 Termination for convenience. Either party may terminate this Agreement for "
            "convenience on ninety (90) days' written notice. If Customer terminates for "
            "convenience, Customer shall pay an early termination fee equal to fifteen percent "
            "(15%) of the remaining minimum annual commitment.\n"
            "9.2 Termination for cause. Either party may terminate for material breach that "
            "remains uncured thirty (30) days after written notice describing the breach.\n"
            "9.3 Insolvency. Either party may terminate immediately if the other becomes insolvent.\n"
            "9.4 Effect of termination. Vendor shall return or destroy Customer data within thirty "
            "(30) days and provide transition assistance for up to sixty (60) days at current rates."
        ),
    ),
    DemoDoc(
        filename="brightline_analytics_subscription.txt",
        title="Software Subscription Agreement - Brightline Analytics",
        owner=MANAGER_EMAIL,
        classification=DocumentClassification.RESTRICTED,
        text=(
            "SOFTWARE SUBSCRIPTION AGREEMENT between Acme Corp (Customer) and Brightline Analytics "
            "Inc. (Vendor) for the Brightline forecasting platform, 250 named users.\n"
            "1. Subscription term. Initial term of twelve (12) months, renewing automatically for "
            "successive twelve-month terms unless either party gives notice of non-renewal at least "
            "sixty (60) days before the renewal date.\n"
            "2. Fees. USD 186,000 per year, payable annually in advance.\n"
            "11. Termination.\n"
            "11.1 After the initial term, Customer may terminate for convenience on sixty (60) days' "
            "written notice. Prepaid fees are non-refundable, except that if Vendor terminates for "
            "convenience it shall refund prepaid fees pro rata.\n"
            "11.2 Vendor may suspend the service if undisputed fees are more than forty-five (45) "
            "days overdue, and may terminate if non-payment is not cured within fifteen (15) days "
            "of a suspension notice.\n"
            "11.3 Data export. For forty-five (45) days after termination, Customer may export its "
            "data in CSV or Parquet format at no charge."
        ),
    ),
    DemoDoc(
        filename="fy2026_q3_budget_variance.txt",
        title="FY2026 Q3 Budget Variance Report",
        owner=MANAGER_EMAIL,
        classification=DocumentClassification.RESTRICTED,
        text=(
            "FY2026 Q3 BUDGET VARIANCE REPORT - Finance.\n"
            "Operating expenses were USD 4.82M against a plan of USD 4.63M (+4.1%). Freight costs "
            "ran 7% over plan due to fuel surcharges; software subscriptions were 2% under plan. "
            "Headcount ended the quarter at 212 against a plan of 218. Recommended actions: renegotiate "
            "the fuel surcharge cap and defer two open requisitions to Q4."
        ),
    ),
    DemoDoc(
        filename="employee_travel_policy_2026.txt",
        title="Employee Travel Policy 2026",
        owner=ANALYST_EMAIL,
        classification=DocumentClassification.INTERNAL,
        text=(
            "EMPLOYEE TRAVEL POLICY 2026.\n"
            "Book economy fares at least fourteen (14) days before departure. Hotel stays are capped "
            "at USD 220 per night in tier-one cities and USD 160 elsewhere. Submit expense reports "
            "with itemized receipts within ten (10) business days of returning. Ride-share is "
            "preferred over rental cars for trips under 50 miles."
        ),
    ),
    DemoDoc(
        filename="office_facilities_guide.txt",
        title="Office Facilities and Visitor Guide",
        owner=ANALYST_EMAIL,
        classification=DocumentClassification.INTERNAL,
        text=(
            "OFFICE FACILITIES AND VISITOR GUIDE.\n"
            "The office is open 7:00-19:00 on weekdays. Visitors must be registered at reception by "
            "their host one business day in advance and wear a badge at all times. Meeting rooms are "
            "booked through the calendar system; release unused bookings within 15 minutes."
        ),
    ),
    DemoDoc(
        filename="it_acceptable_use_policy.txt",
        title="IT Acceptable Use Policy",
        owner=ANALYST_EMAIL,
        classification=DocumentClassification.INTERNAL,
        text=(
            "IT ACCEPTABLE USE POLICY.\n"
            "Company laptops must use full-disk encryption and lock after five minutes of inactivity. "
            "Report a lost or stolen device to the service desk within one hour. Do not install "
            "unapproved software or store company data in personal cloud accounts. Multi-factor "
            "authentication is required for all remote access."
        ),
    ),
]


async def _upsert_user(
    db, email: str, role: UserRole, full_name: str, department: str, manager_id=None
) -> User:
    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            username=f"mcp-demo-{email.split('.')[0]}",
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        )
        db.add(user)
    user.full_name = full_name
    user.role = role
    user.department = department
    user.manager_id = manager_id
    user.is_active = True
    user.is_verified = True
    await db.flush()
    return user


async def _upsert_document(db, spec: DemoDoc, owner: User) -> Document:
    doc = (
        await db.execute(
            select(Document).where(
                Document.document_set_id == DOCUMENT_SET_ID,
                Document.filename == spec.filename,
            )
        )
    ).scalar_one_or_none()
    if doc is None:
        doc = Document(document_set_id=DOCUMENT_SET_ID, filename=spec.filename)
        db.add(doc)
    doc.title = spec.title
    doc.file_type = "txt"
    doc.file_size = len(spec.text.encode())
    doc.file_hash = hashlib.sha256(spec.text.encode()).hexdigest()
    doc.storage_path = f"synthetic://{DOCUMENT_SET_ID}/{spec.filename}"
    doc.status = "indexed"
    doc.virus_scan_status = "clean"
    doc.full_text = spec.text
    doc.description = spec.text.split("\n", 1)[0][:300]
    doc.language = "en"
    doc.tags = [DOCUMENT_SET_ID, "synthetic"]
    doc.classification = spec.classification
    doc.uploaded_by = owner.id
    metadata = dict(doc.custom_metadata or {})
    metadata["visibility"] = GRANT_VISIBILITY
    doc.custom_metadata = metadata
    await db.flush()
    return doc


async def _upsert_gemini(db) -> User:
    user = (
        await db.execute(select(User).where(User.email == GEMINI_EMAIL))
    ).scalar_one_or_none()
    if user is None:
        user = User(
            email=GEMINI_EMAIL,
            username=GEMINI_USERNAME,
            hashed_password=get_password_hash(GEMINI_PASSWORD),
        )
        db.add(user)
    user.full_name = "Gemini"
    user.role = UserRole.MANAGER
    user.department = "Demo"
    user.manager_id = None
    user.is_active = True
    user.is_verified = True
    user.hashed_password = get_password_hash(GEMINI_PASSWORD)
    await db.flush()
    return user


async def _grant_read(db, document: Document, grantee: User, granter: User) -> None:
    existing = (
        await db.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == document.id,
                DocumentPermission.user_id == grantee.id,
                DocumentPermission.permission_type == "read",
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            DocumentPermission(
                document_id=document.id,
                user_id=grantee.id,
                permission_type="read",
                granted_by=granter.id,
                reason="Gemini demo corpus",
            )
        )
        await db.flush()


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        manager = await _upsert_user(
            db, MANAGER_EMAIL, UserRole.MANAGER, "Morgan Reyes (demo)", "Finance"
        )
        analyst = await _upsert_user(
            db,
            ANALYST_EMAIL,
            UserRole.ANALYST,
            "Avery Chen (demo)",
            "Operations",
            manager_id=manager.id,
        )
        gemini = await _upsert_gemini(db)
        owners = {MANAGER_EMAIL: manager, ANALYST_EMAIL: analyst}
        docs = [
            await _upsert_document(db, spec, owners[spec.owner]) for spec in DEMO_DOCS
        ]
        for doc in docs:
            granter = manager if doc.uploaded_by == manager.id else analyst
            await _grant_read(db, doc, gemini, granter)
        await db.commit()
        for doc in docs:
            await db.refresh(doc)
        index_items: List[Tuple[str, str, Dict]] = [
            (
                str(doc.uuid),
                doc.full_text,
                SearchService()._document_index_metadata(doc),
            )
            for doc in docs
        ]
        rows = [
            (doc.title, str(doc.uuid), doc.classification.value, doc.uploaded_by)
            for doc in docs
        ]

    es = ElasticsearchService()
    try:
        if not await es.ensure_index_exists():
            raise SystemExit("Elasticsearch index unavailable")
        for doc_id, text, metadata in index_items:
            if not await es.index_document(doc_id, text, metadata):
                raise SystemExit(f"Elasticsearch indexing failed for {doc_id}")
        await es.client.indices.refresh(index=es.index_name)
    finally:
        await es.client.close()

    qdrant = QdrantService()
    for doc_id, text, metadata in index_items:
        await asyncio.to_thread(
            qdrant.index_document_sync, doc_id, text, dict(metadata)
        )

    print(
        f"Users: {MANAGER_EMAIL} (Manager, id={manager.id}), "
        f"{ANALYST_EMAIL} (Analyst, id={analyst.id}), "
        f"{GEMINI_EMAIL} (Manager, id={gemini.id})"
    )
    for title, doc_id, classification, owner_id in rows:
        print(f"  {classification:<10} owner={owner_id:<5} {doc_id}  {title}")
    print(f"Indexed {len(index_items)} documents in Elasticsearch and Qdrant.")


async def purge() -> None:
    async with AsyncSessionLocal() as db:
        docs = (
            (
                await db.execute(
                    select(Document).where(Document.document_set_id == DOCUMENT_SET_ID)
                )
            )
            .scalars()
            .all()
        )
        doc_ids = [str(doc.uuid) for doc in docs]
        for doc in docs:
            await db.delete(doc)
        users = (
            (
                await db.execute(
                    select(User).where(
                        User.email.in_([MANAGER_EMAIL, ANALYST_EMAIL, GEMINI_EMAIL])
                    )
                )
            )
            .scalars()
            .all()
        )
        for user in users:
            user.is_active = False
        await db.commit()

    es = ElasticsearchService()
    try:
        for doc_id in doc_ids:
            try:
                await es.client.delete(index=es.index_name, id=doc_id)
            except Exception as exc:
                print(f"  Elasticsearch delete skipped for {doc_id}: {exc}")
    finally:
        await es.client.close()

    qdrant = QdrantService()
    for doc_id in doc_ids:
        await asyncio.to_thread(qdrant.delete_document, doc_id)

    print(
        f"Removed {len(doc_ids)} demo documents; deactivated {len(users)} demo users."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed or purge the MCP connector demo dataset."
    )
    parser.add_argument(
        "--purge",
        action="store_true",
        help="remove demo documents and deactivate demo users",
    )
    args = parser.parse_args()
    async_engine.sync_engine.echo = False
    asyncio.run(purge() if args.purge else seed())


if __name__ == "__main__":
    main()
