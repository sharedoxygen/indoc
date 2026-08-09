"""
Tests for user hierarchy and role-based access control
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.document import Document
from app.core.security import create_access_token
from app.core.document_scope import get_effective_document_ids


@pytest.mark.asyncio
async def test_assign_manager_to_analyst(
    client: AsyncClient,
    test_db: AsyncSession,
    test_admin_user: User,
    test_manager_user: User,
    test_analyst_user: User
):
    """Test assigning a manager to an analyst"""
    admin_token = create_access_token(data={"sub": str(test_admin_user.id)})
    
    response = await client.post(
        f"/api/v1/users/{test_analyst_user.id}/assign-manager",
        params={"manager_id": test_manager_user.id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    assert "Manager assigned successfully" in response.json()["message"]


@pytest.mark.asyncio
async def test_manager_cannot_assign_manager(
    client: AsyncClient,
    test_manager_user: User,
    test_analyst_user: User
):
    """Test that managers cannot assign other managers"""
    manager_token = create_access_token(data={"sub": str(test_manager_user.id)})
    
    response = await client.post(
        f"/api/v1/users/{test_analyst_user.id}/assign-manager",
        params={"manager_id": test_manager_user.id},
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_team_analysts_as_manager(
    client: AsyncClient,
    test_manager_user: User,
    test_analyst_user: User
):
    """Test that managers can list their team analysts"""
    manager_token = create_access_token(data={"sub": str(test_manager_user.id)})
    
    response = await client.get(
        "/api/v1/users/team/analysts",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    
    assert response.status_code == 200
    analysts = response.json()
    assert len(analysts) >= 1
    assert any(a["email"] == test_analyst_user.email for a in analysts)


@pytest.mark.asyncio
async def test_analyst_cannot_list_team(
    client: AsyncClient,
    test_analyst_user: User
):
    """Test that analysts cannot list team members"""
    analyst_token = create_access_token(data={"sub": str(test_analyst_user.id)})
    
    response = await client.get(
        "/api/v1/users/team/analysts",
        headers={"Authorization": f"Bearer {analyst_token}"}
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_document_scope_admin_sees_all(
    test_db: AsyncSession,
    test_admin_user: User,
    test_manager_user: User,
    test_analyst_user: User
):
    """Test that admin sees all documents"""
    # Create documents for different users
    doc1 = Document(
        filename="admin_doc.txt",
        storage_path="/test/admin_doc.txt",
        file_type="text/plain",
        file_size=100,
        uploaded_by=test_admin_user.id
    )
    doc2 = Document(
        filename="manager_doc.txt",
        storage_path="/test/manager_doc.txt",
        file_type="text/plain",
        file_size=100,
        uploaded_by=test_manager_user.id
    )
    doc3 = Document(
        filename="analyst_doc.txt",
        storage_path="/test/analyst_doc.txt",
        file_type="text/plain",
        file_size=100,
        uploaded_by=test_analyst_user.id
    )
    
    test_db.add_all([doc1, doc2, doc3])
    await test_db.commit()
    
    # Admin should see all documents
    effective_ids = await get_effective_document_ids(test_db, test_admin_user)
    assert len(effective_ids) >= 3


@pytest.mark.asyncio
async def test_document_scope_manager_sees_team_docs(
    test_db: AsyncSession,
    test_manager_user: User,
    test_analyst_user: User
):
    """Test that manager sees their own and analysts' documents"""
    # Create documents
    manager_doc = Document(
        filename="manager_doc.txt",
        storage_path="/test/manager_doc.txt",
        file_type="text/plain",
        file_size=100,
        uploaded_by=test_manager_user.id
    )
    analyst_doc = Document(
        filename="analyst_doc.txt",
        storage_path="/test/analyst_doc.txt",
        file_type="text/plain",
        file_size=100,
        uploaded_by=test_analyst_user.id
    )
    
    test_db.add_all([manager_doc, analyst_doc])
    await test_db.commit()
    await test_db.refresh(manager_doc)
    await test_db.refresh(analyst_doc)
    
    # Manager should see both documents
    effective_ids = await get_effective_document_ids(test_db, test_manager_user)
    assert manager_doc.id in effective_ids
    assert analyst_doc.id in effective_ids


@pytest.mark.asyncio
async def test_document_scope_analyst_sees_own_only(
    test_db: AsyncSession,
    test_analyst_user: User,
    test_manager_user: User
):
    """Test that analyst sees only their own documents"""
    # Create documents
    analyst_doc = Document(
        filename="analyst_doc.txt",
        storage_path="/test/analyst_doc.txt",
        file_type="text/plain",
        file_size=100,
        uploaded_by=test_analyst_user.id
    )
    manager_doc = Document(
        filename="manager_doc.txt",
        storage_path="/test/manager_doc.txt",
        file_type="text/plain",
        file_size=100,
        uploaded_by=test_manager_user.id
    )
    
    test_db.add_all([analyst_doc, manager_doc])
    await test_db.commit()
    await test_db.refresh(analyst_doc)
    await test_db.refresh(manager_doc)
    
    # Analyst should see only their own document
    effective_ids = await get_effective_document_ids(test_db, test_analyst_user)
    assert analyst_doc.id in effective_ids
    assert manager_doc.id not in effective_ids


@pytest.mark.asyncio
async def test_document_scope_with_selection(
    test_db: AsyncSession,
    test_admin_user: User
):
    """Test that document selection narrows the scope"""
    # Create documents
    doc1 = Document(
        filename="doc1.txt",
        storage_path="/test/doc1.txt",
        file_type="text/plain",
        file_size=100,
        uploaded_by=test_admin_user.id
    )
    doc2 = Document(
        filename="doc2.txt",
        storage_path="/test/doc2.txt",
        file_type="text/plain",
        file_size=100,
        uploaded_by=test_admin_user.id
    )
    
    test_db.add_all([doc1, doc2])
    await test_db.commit()
    await test_db.refresh(doc1)
    await test_db.refresh(doc2)
    
    # Admin selects only doc1
    selected_ids = {doc1.id}
    effective_ids = await get_effective_document_ids(test_db, test_admin_user, selected_ids)
    
    assert len(effective_ids) == 1
    assert doc1.id in effective_ids
    assert doc2.id not in effective_ids


@pytest.mark.asyncio
async def test_unassign_manager(
    client: AsyncClient,
    test_db: AsyncSession,
    test_admin_user: User,
    test_analyst_user: User
):
    """Test unassigning a manager from an analyst"""
    admin_token = create_access_token(data={"sub": str(test_admin_user.id)})
    
    response = await client.post(
        f"/api/v1/users/{test_analyst_user.id}/unassign-manager",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    assert "Manager unassigned successfully" in response.json()["message"]
    
    # Verify manager_id is None
    await test_db.refresh(test_analyst_user)
    assert test_analyst_user.manager_id is None

