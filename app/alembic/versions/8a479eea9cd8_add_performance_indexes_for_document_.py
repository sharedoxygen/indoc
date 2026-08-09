"""add_performance_indexes_for_document_queries

Revision ID: 8a479eea9cd8
Revises: 033afc30105d
Create Date: 2025-10-07 00:57:38.592368+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a479eea9cd8'
down_revision = '033afc30105d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add performance indexes for frequently queried document columns"""
    
    # Composite index for tenant-based queries (most common filter)
    op.create_index(
        'idx_documents_tenant_uploaded_by',
        'documents',
        ['tenant_id', 'uploaded_by'],
        unique=False
    )
    
    # Index for status filtering (very common in list queries)
    op.create_index(
        'idx_documents_status',
        'documents',
        ['status'],
        unique=False
    )
    
    # Index for file_type filtering
    op.create_index(
        'idx_documents_file_type',
        'documents',
        ['file_type'],
        unique=False
    )
    
    # Composite index for common sorting by created_at with filters
    op.create_index(
        'idx_documents_status_created_at',
        'documents',
        ['status', 'created_at'],
        unique=False
    )
    
    # Composite index for updated_at sorting with filters
    op.create_index(
        'idx_documents_status_updated_at',
        'documents',
        ['status', 'updated_at'],
        unique=False
    )
    
    # Index for filename search (lowercase for case-insensitive searches)
    # Note: PostgreSQL supports functional indexes
    op.execute('CREATE INDEX idx_documents_filename_lower ON documents (LOWER(filename))')
    
    # Index for title search
    op.execute('CREATE INDEX idx_documents_title_lower ON documents (LOWER(title))')


def downgrade() -> None:
    """Remove performance indexes"""
    
    op.drop_index('idx_documents_title_lower', table_name='documents')
    op.drop_index('idx_documents_filename_lower', table_name='documents')
    op.drop_index('idx_documents_status_updated_at', table_name='documents')
    op.drop_index('idx_documents_status_created_at', table_name='documents')
    op.drop_index('idx_documents_file_type', table_name='documents')
    op.drop_index('idx_documents_status', table_name='documents')
    op.drop_index('idx_documents_tenant_uploaded_by', table_name='documents')