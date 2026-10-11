"""Grant-restricted documents stay out of the personal library."""

import pytest

from app.core.document_scope import get_effective_document_ids
from app.core.security import get_password_hash
from app.models.classification import DocumentClassification
from app.models.document import Document
from app.models.document_permission import DocumentPermission
from app.models.user import User, UserRole


def _doc(filename, owner_id, classification, grant_only):
    return Document(
        filename=filename,
        storage_path=f"/test/{filename}",
        file_type="text/plain",
        file_size=100,
        uploaded_by=owner_id,
        classification=classification,
        custom_metadata={"visibility": "grant"} if grant_only else {},
    )


@pytest.mark.asyncio
async def test_admin_library_excludes_grant_restricted_documents(
    test_db, test_admin_user, test_manager_user
):
    personal = _doc(
        "personal.txt", test_manager_user.id, DocumentClassification.INTERNAL, False
    )
    demo = _doc(
        "demo.txt", test_manager_user.id, DocumentClassification.RESTRICTED, True
    )
    test_db.add_all([personal, demo])
    await test_db.commit()
    await test_db.refresh(personal)
    await test_db.refresh(demo)

    visible = await get_effective_document_ids(test_db, test_admin_user)

    assert personal.id in visible
    assert demo.id not in visible


@pytest.mark.asyncio
async def test_read_grant_admits_grantee_and_respects_clearance(
    test_db, test_manager_user, test_analyst_user
):
    demo = _doc(
        "contract.txt",
        test_manager_user.id,
        DocumentClassification.RESTRICTED,
        True,
    )
    gemini = User(
        email="gemini@example.com",
        username="gemini",
        full_name="Gemini",
        hashed_password=get_password_hash("GeminiDemo123!"),
        role=UserRole.MANAGER,
        is_active=True,
        is_verified=True,
    )
    test_db.add_all([demo, gemini])
    await test_db.commit()
    await test_db.refresh(demo)
    await test_db.refresh(gemini)

    test_db.add(
        DocumentPermission(
            document_id=demo.id,
            user_id=gemini.id,
            permission_type="read",
            granted_by=test_manager_user.id,
            reason="demo",
        )
    )
    test_db.add(
        DocumentPermission(
            document_id=demo.id,
            user_id=test_analyst_user.id,
            permission_type="read",
            granted_by=test_manager_user.id,
            reason="demo",
        )
    )
    await test_db.commit()

    gemini_ids = await get_effective_document_ids(test_db, gemini)
    analyst_ids = await get_effective_document_ids(test_db, test_analyst_user)

    assert demo.id in gemini_ids
    assert demo.id not in analyst_ids
