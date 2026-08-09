"""rename_weaviate_id_to_qdrant_id

Revision ID: 1930c41ac152
Revises: e80b18f8826b
Create Date: 2025-10-13 00:18:01.554594+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1930c41ac152'
down_revision = 'e80b18f8826b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Rename weaviate_id column to qdrant_id in documents table.
    
    This migration is part of the Weaviate → Qdrant vector database migration.
    The column is simply renamed; existing values are preserved for data continuity.
    """
    # Rename column
    op.alter_column('documents', 'weaviate_id', new_column_name='qdrant_id')


def downgrade() -> None:
    """Rollback: rename qdrant_id back to weaviate_id"""
    op.alter_column('documents', 'qdrant_id', new_column_name='weaviate_id')