"""fix_classification_enum_values

Revision ID: 033afc30105d
Revises: add_folder_hierarchy
Create Date: 2025-10-05 00:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '033afc30105d'
down_revision = 'add_folder_hierarchy'
branch_labels = None
depends_on = None


def upgrade():
    # PostgreSQL enum migration requires special handling
    # We need to:
    # 1. Add new enum values
    # 2. Update existing data
    # 3. Remove old enum values (optional, or keep for backward compatibility)
    
    # Since we can't easily modify enums in PostgreSQL, we'll:
    # 1. Create a temporary column
    # 2. Copy and transform data
    # 3. Drop old column
    # 4. Rename temp column
    
    # Add temporary column
    op.add_column('documents', sa.Column('classification_new', sa.String(50), nullable=True))
    
    # Copy and transform data - map old values to new
    op.execute("""
        UPDATE documents 
        SET classification_new = CASE 
            WHEN classification = 'Public' THEN 'PUBLIC'
            WHEN classification = 'Internal' THEN 'INTERNAL'
            WHEN classification = 'Restricted' THEN 'RESTRICTED'
            WHEN classification = 'Confidential' THEN 'CONFIDENTIAL'
            ELSE 'INTERNAL'
        END
    """)
    
    # Drop old enum column
    op.drop_column('documents', 'classification')
    
    # Create new enum type with correct values
    op.execute("CREATE TYPE documentclassification_new AS ENUM ('PUBLIC', 'INTERNAL', 'RESTRICTED', 'CONFIDENTIAL')")
    
    # Add new column with proper enum type
    op.add_column('documents', 
        sa.Column('classification', 
            sa.Enum('PUBLIC', 'INTERNAL', 'RESTRICTED', 'CONFIDENTIAL', 
                    name='documentclassification_new', 
                    create_type=False),
            nullable=False,
            server_default='INTERNAL'
        )
    )
    
    # Copy data from temp column
    op.execute("""
        UPDATE documents 
        SET classification = classification_new::documentclassification_new
    """)
    
    # Drop temp column
    op.drop_column('documents', 'classification_new')
    
    # Drop old enum type
    op.execute("DROP TYPE IF EXISTS documentclassification")
    
    # Rename new enum type to original name
    op.execute("ALTER TYPE documentclassification_new RENAME TO documentclassification")
    
    # Create index
    op.create_index('ix_documents_classification', 'documents', ['classification'], unique=False)


def downgrade():
    # Reverse the migration if needed
    op.drop_index('ix_documents_classification', table_name='documents')
    
    # Add temp column
    op.add_column('documents', sa.Column('classification_old', sa.String(50), nullable=True))
    
    # Transform back
    op.execute("""
        UPDATE documents 
        SET classification_old = CASE 
            WHEN classification = 'PUBLIC' THEN 'Public'
            WHEN classification = 'INTERNAL' THEN 'Internal'
            WHEN classification = 'RESTRICTED' THEN 'Restricted'
            WHEN classification = 'CONFIDENTIAL' THEN 'Confidential'
            ELSE 'Internal'
        END
    """)
    
    # Drop new column
    op.drop_column('documents', 'classification')
    
    # Recreate old enum
    op.execute("CREATE TYPE documentclassification_old AS ENUM ('Public', 'Internal', 'Restricted', 'Confidential')")
    
    # Add old column
    op.add_column('documents',
        sa.Column('classification',
            sa.Enum('Public', 'Internal', 'Restricted', 'Confidential',
                    name='documentclassification_old',
                    create_type=False),
            nullable=False,
            server_default='Internal'
        )
    )
    
    # Copy data
    op.execute("""
        UPDATE documents 
        SET classification = classification_old::documentclassification_old
    """)
    
    # Drop temp
    op.drop_column('documents', 'classification_old')
    
    # Drop new enum
    op.execute("DROP TYPE IF EXISTS documentclassification")
    
    # Rename old enum
    op.execute("ALTER TYPE documentclassification_old RENAME TO documentclassification")
