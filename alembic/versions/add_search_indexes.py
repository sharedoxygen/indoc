"""Add search performance indexes

Revision ID: add_search_indexes
Revises: 001_initial_schema
Create Date: 2025-09-04 21:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_search_indexes'
down_revision = '6b41d60cf269'
branch_labels = None
depends_on = None


def upgrade():
    # Add indexes for search performance
    op.create_index('idx_documents_status', 'documents', ['status'])
    op.create_index('idx_documents_file_type', 'documents', ['file_type'])
    op.create_index('idx_documents_created_at', 'documents', ['created_at'])
    op.create_index('idx_documents_updated_at', 'documents', ['updated_at'])
    op.create_index('idx_documents_uploaded_by', 'documents', ['uploaded_by'])
    
    # Add composite indexes for common query patterns
    op.create_index('idx_documents_status_created', 'documents', ['status', 'created_at'])
    op.create_index('idx_documents_status_uploaded_by', 'documents', ['status', 'uploaded_by'])
    
    # Add GIN index for full text search on PostgreSQL
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_fulltext_gin 
        ON documents USING gin(to_tsvector('english', 
            COALESCE(filename, '') || ' ' || 
            COALESCE(title, '') || ' ' || 
            COALESCE(description, '') || ' ' || 
            COALESCE(full_text, '')
        ))
    """)
    
    # Add trigram index for fuzzy search (requires pg_trgm extension)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_filename_trgm 
        ON documents USING gin(filename gin_trgm_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_documents_title_trgm 
        ON documents USING gin(title gin_trgm_ops)
    """)


def downgrade():
    # Remove indexes
    op.drop_index('idx_documents_title_trgm', 'documents')
    op.drop_index('idx_documents_filename_trgm', 'documents')
    op.drop_index('idx_documents_fulltext_gin', 'documents')
    op.drop_index('idx_documents_status_uploaded_by', 'documents')
    op.drop_index('idx_documents_status_created', 'documents')
    op.drop_index('idx_documents_uploaded_by', 'documents')
    op.drop_index('idx_documents_updated_at', 'documents')
    op.drop_index('idx_documents_created_at', 'documents')
    op.drop_index('idx_documents_file_type', 'documents')
    op.drop_index('idx_documents_status', 'documents')
