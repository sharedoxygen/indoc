"""add_token_revocation_table

Revision ID: 3e28b86ede48
Revises: 67bd2a8667f3
Create Date: 2025-10-03 20:04:00.721000+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3e28b86ede48'
down_revision = '67bd2a8667f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create revoked_tokens table
    op.create_table(
        'revoked_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('jti', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_type', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=True),
        sa.Column('expires_at', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_revoked_token_jti', 'revoked_tokens', ['jti'], unique=True)
    op.create_index('idx_revoked_token_user', 'revoked_tokens', ['user_id'], unique=False)
    op.create_index('idx_revoked_token_expires', 'revoked_tokens', ['expires_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_revoked_token_expires', table_name='revoked_tokens')
    op.drop_index('idx_revoked_token_user', table_name='revoked_tokens')
    op.drop_index('idx_revoked_token_jti', table_name='revoked_tokens')
    
    # Drop table
    op.drop_table('revoked_tokens')