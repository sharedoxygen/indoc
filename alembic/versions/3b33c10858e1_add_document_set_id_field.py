"""add_document_set_id_field

Revision ID: 3b33c10858e1
Revises: 052fbe3847f1
Create Date: 2025-10-09 18:10:40.129402+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b33c10858e1'
down_revision = '052fbe3847f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add document_set_id column to documents table
    op.add_column('documents', sa.Column('document_set_id', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_documents_document_set_id'), 'documents', ['document_set_id'], unique=False)


def downgrade() -> None:
    # Remove document_set_id column from documents table
    op.drop_index(op.f('ix_documents_document_set_id'), table_name='documents')
    op.drop_column('documents', 'document_set_id')