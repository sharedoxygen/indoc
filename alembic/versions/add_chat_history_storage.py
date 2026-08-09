"""Add chat history storage and retention tables

Revision ID: add_chat_history_storage
Revises: e496beaf6de7
Create Date: 2025-10-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_chat_history_storage'
down_revision = 'e496beaf6de7'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_storage_quotas table
    op.create_table('user_storage_quotas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('conversation_storage_limit', sa.BigInteger(), nullable=True, server_default='10485760'),
        sa.Column('document_storage_limit', sa.BigInteger(), nullable=True, server_default='104857600'),
        sa.Column('conversation_retention_days', sa.Integer(), nullable=True, server_default='90'),
        sa.Column('document_retention_days', sa.Integer(), nullable=True, server_default='365'),
        sa.Column('is_premium', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('premium_tier', sa.String(length=50), nullable=True, server_default='free'),
        sa.Column('premium_expires_at', sa.DateTime(), nullable=True),
        sa.Column('current_conversation_storage', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('current_document_storage', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('conversation_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('message_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('monthly_fee', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('overage_charges', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('last_billed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_storage_quotas_id'), 'user_storage_quotas', ['id'], unique=False)
    
    # Create storage_usage_history table
    op.create_table('storage_usage_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('quota_id', sa.Integer(), nullable=False),
        sa.Column('conversation_storage_used', sa.BigInteger(), nullable=False),
        sa.Column('document_storage_used', sa.BigInteger(), nullable=False),
        sa.Column('conversation_count', sa.Integer(), nullable=False),
        sa.Column('message_count', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('storage_cost', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('overage_cost', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('total_cost', sa.Float(), nullable=True, server_default='0.0'),
        sa.ForeignKeyConstraint(['quota_id'], ['user_storage_quotas.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_storage_usage_history_id'), 'storage_usage_history', ['id'], unique=False)
    op.create_index('ix_storage_usage_history_quota_period', 'storage_usage_history', ['quota_id', 'period_start'], unique=False)
    
    # Create conversation_retention table
    op.create_table('conversation_retention',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_compressed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_deleted', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.Column('scheduled_deletion_at', sa.DateTime(), nullable=True),
        sa.Column('original_size', sa.BigInteger(), nullable=False),
        sa.Column('compressed_size', sa.BigInteger(), nullable=True),
        sa.Column('storage_location', sa.String(length=500), nullable=True),
        sa.Column('is_pinned', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_favorite', sa.Boolean(), nullable=True, server_default='false'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conversation_id')
    )
    op.create_index(op.f('ix_conversation_retention_id'), 'conversation_retention', ['id'], unique=False)
    op.create_index('ix_conversation_retention_user_archived', 'conversation_retention', ['user_id', 'is_archived'], unique=False)
    op.create_index('ix_conversation_retention_scheduled_deletion', 'conversation_retention', ['scheduled_deletion_at'], unique=False)
    
    # Add indexes for better query performance
    op.create_index('ix_conversations_user_updated', 'conversations', ['user_id', 'updated_at'], unique=False)
    op.create_index('ix_messages_conversation_created', 'messages', ['conversation_id', 'created_at'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index('ix_messages_conversation_created', table_name='messages')
    op.drop_index('ix_conversations_user_updated', table_name='conversations')
    op.drop_index('ix_conversation_retention_scheduled_deletion', table_name='conversation_retention')
    op.drop_index('ix_conversation_retention_user_archived', table_name='conversation_retention')
    op.drop_index(op.f('ix_conversation_retention_id'), table_name='conversation_retention')
    op.drop_table('conversation_retention')
    op.drop_index('ix_storage_usage_history_quota_period', table_name='storage_usage_history')
    op.drop_index(op.f('ix_storage_usage_history_id'), table_name='storage_usage_history')
    op.drop_table('storage_usage_history')
    op.drop_index(op.f('ix_user_storage_quotas_id'), table_name='user_storage_quotas')
    op.drop_table('user_storage_quotas')
