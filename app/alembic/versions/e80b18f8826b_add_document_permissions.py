"""add_document_permissions

Revision ID: e80b18f8826b
Revises: c528546b2df9
Create Date: 2025-10-08 00:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = 'e80b18f8826b'
down_revision = 'c528546b2df9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create document_permissions table
    op.create_table(
        'document_permissions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('permission_type', sa.String(20), nullable=False),  # 'read', 'write', 'share', 'delete'
        sa.Column('granted_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('granted_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.UniqueConstraint('document_id', 'user_id', 'permission_type', name='uq_doc_user_permission')
    )
    
    # Create indexes for performance
    op.create_index('idx_doc_permissions_document', 'document_permissions', ['document_id'])
    op.create_index('idx_doc_permissions_user', 'document_permissions', ['user_id'])
    op.create_index('idx_doc_permissions_granted_by', 'document_permissions', ['granted_by'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_doc_permissions_granted_by', table_name='document_permissions')
    op.drop_index('idx_doc_permissions_user', table_name='document_permissions')
    op.drop_index('idx_doc_permissions_document', table_name='document_permissions')
    
    # Drop table
    op.drop_table('document_permissions')
