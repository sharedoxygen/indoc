"""Add multi-tenancy support

Revision ID: add_multi_tenancy_001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_multi_tenancy_001'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('quota_documents', sa.Integer(), default=10000),
        sa.Column('quota_storage_gb', sa.Integer(), default=100),
        sa.Column('quota_users', sa.Integer(), default=50),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add tenant_id to existing tables
    op.add_column('users', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('documents', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('documents', sa.Column('folder_structure', sa.String(500), nullable=True))
    op.add_column('documents', sa.Column('processing_status', sa.String(50), nullable=True, default='pending'))
    
    # Create indexes for tenant_id
    op.create_index('idx_users_tenant', 'users', ['tenant_id'])
    op.create_index('idx_documents_tenant', 'documents', ['tenant_id'])
    op.create_index('idx_documents_folder', 'documents', ['folder_structure'])
    
    # Create conversations table
    op.create_table('conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('conversation_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_conversations_tenant', 'conversations', ['tenant_id'])
    op.create_index('idx_conversations_user', 'conversations', ['user_id'])
    
    # Create messages table
    op.create_table('messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_messages_conversation', 'messages', ['conversation_id'])
    op.create_index('idx_messages_created', 'messages', ['created_at'])
    
    # Create tenant usage tracking table
    op.create_table('tenant_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('documents_count', sa.Integer(), default=0),
        sa.Column('storage_bytes', sa.BigInteger(), default=0),
        sa.Column('api_calls', sa.Integer(), default=0),
        sa.Column('llm_tokens', sa.Integer(), default=0),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_unique_constraint('uq_tenant_usage_date', 'tenant_usage', ['tenant_id', 'date'])
    
    # Add foreign key constraints after adding tenant_id columns
    op.create_foreign_key('fk_users_tenant', 'users', 'tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_documents_tenant', 'documents', 'tenants', ['tenant_id'], ['id'])


def downgrade():
    # Drop foreign key constraints
    op.drop_constraint('fk_documents_tenant', 'documents', type_='foreignkey')
    op.drop_constraint('fk_users_tenant', 'users', type_='foreignkey')
    
    # Drop tables
    op.drop_table('tenant_usage')
    op.drop_table('messages')
    op.drop_table('conversations')
    
    # Drop indexes
    op.drop_index('idx_documents_folder', 'documents')
    op.drop_index('idx_documents_tenant', 'documents')
    op.drop_index('idx_users_tenant', 'users')
    
    # Drop columns
    op.drop_column('documents', 'processing_status')
    op.drop_column('documents', 'folder_structure')
    op.drop_column('documents', 'tenant_id')
    op.drop_column('users', 'tenant_id')
    
    # Drop tenants table
    op.drop_table('tenants')