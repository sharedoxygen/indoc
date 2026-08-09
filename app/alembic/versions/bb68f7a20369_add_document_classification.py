"""add_document_classification

Revision ID: bb68f7a20369
Revises: 3e28b86ede48
Create Date: 2025-10-03 20:12:14.779823+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'bb68f7a20369'
down_revision = '3e28b86ede48'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create DocumentClassification enum type
    document_classification_enum = postgresql.ENUM(
        'Public', 'Internal', 'Restricted', 'Confidential',
        name='documentclassification',
        create_type=True
    )
    document_classification_enum.create(op.get_bind(), checkfirst=True)
    
    # Add classification column to documents table
    op.add_column(
        'documents',
        sa.Column(
            'classification',
            sa.Enum('Public', 'Internal', 'Restricted', 'Confidential', name='documentclassification'),
            nullable=False,
            server_default='Internal'
        )
    )
    
    # Create index on classification for efficient filtering
    op.create_index('ix_documents_classification', 'documents', ['classification'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_documents_classification', table_name='documents')
    
    # Drop column
    op.drop_column('documents', 'classification')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS documentclassification')