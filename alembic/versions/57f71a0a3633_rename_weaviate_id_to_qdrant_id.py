"""rename_weaviate_id_to_qdrant_id

Revision ID: 57f71a0a3633
Revises: 3b33c10858e1
Create Date: 2025-10-13 00:19:23.120760+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '57f71a0a3633'
down_revision = '3b33c10858e1'
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