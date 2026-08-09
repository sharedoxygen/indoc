"""add_user_profile_fields

Revision ID: c528546b2df9
Revises: 8a479eea9cd8
Create Date: 2025-10-08 00:24:54.606252+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c528546b2df9'
down_revision = '8a479eea9cd8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user profile fields
    op.add_column('users', sa.Column('department', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('location', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove user profile fields
    op.drop_column('users', 'location')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'department')