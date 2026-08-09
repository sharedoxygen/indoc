"""Add folder hierarchy support to documents

Revision ID: add_folder_hierarchy
Revises: 1c22648fa9b0
Create Date: 2025-10-05 00:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_folder_hierarchy'
down_revision = '1c22648fa9b0'
branch_labels = None
depends_on = None


def upgrade():
    # Add folder path and hierarchy fields to documents
    op.add_column('documents', sa.Column('folder_path', sa.String(length=1000), nullable=True))
    op.add_column('documents', sa.Column('parent_folder_id', sa.Integer(), nullable=True))
    
    # Create index for folder queries
    op.create_index('ix_documents_folder_path', 'documents', ['folder_path'], unique=False)
    
    # Add foreign key for parent folder (self-referencing for folder tree)
    op.create_foreign_key(
        'fk_documents_parent_folder',
        'documents', 'documents',
        ['parent_folder_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    op.drop_constraint('fk_documents_parent_folder', 'documents', type_='foreignkey')
    op.drop_index('ix_documents_folder_path', table_name='documents')
    op.drop_column('documents', 'parent_folder_id')
    op.drop_column('documents', 'folder_path')


