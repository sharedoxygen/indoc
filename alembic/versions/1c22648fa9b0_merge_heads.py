"""merge_heads

Revision ID: 1c22648fa9b0
Revises: add_chat_history_storage, fix_userrole_enum
Create Date: 2025-10-05 03:54:50.873903+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c22648fa9b0'
down_revision = ('add_chat_history_storage', 'fix_userrole_enum')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass