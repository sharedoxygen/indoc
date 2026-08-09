"""add_mfa_fields_to_users

Revision ID: 67bd2a8667f3
Revises: e496beaf6de7
Create Date: 2025-10-03 20:01:50.074474+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67bd2a8667f3'
down_revision = 'e496beaf6de7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add MFA fields to users table
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('mfa_secret', sa.String(length=32), nullable=True))
    op.add_column('users', sa.Column('mfa_backup_codes', sa.String(length=512), nullable=True))


def downgrade() -> None:
    # Remove MFA fields from users table
    op.drop_column('users', 'mfa_backup_codes')
    op.drop_column('users', 'mfa_secret')
    op.drop_column('users', 'mfa_enabled')