"""Fix UserRole enum values to match Python code

Revision ID: fix_userrole_enum
Revises: e496beaf6de7
Create Date: 2025-10-03 19:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fix_userrole_enum'
down_revision = 'bb68f7a20369'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new enum type with correct values
    op.execute("""
        CREATE TYPE userrole_new AS ENUM (
            'Admin', 'Manager', 'Analyst', 
            'Reviewer', 'Uploader', 'Viewer', 'Compliance'
        );
    """)
    
    # Update users table to use new enum with value mapping
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role TYPE userrole_new 
        USING (
            CASE role::text
                WHEN 'ADMIN' THEN 'Admin'::userrole_new
                WHEN 'REVIEWER' THEN 'Reviewer'::userrole_new
                WHEN 'UPLOADER' THEN 'Uploader'::userrole_new
                WHEN 'VIEWER' THEN 'Viewer'::userrole_new
                WHEN 'COMPLIANCE' THEN 'Compliance'::userrole_new
                WHEN 'Manager' THEN 'Manager'::userrole_new
                WHEN 'Analyst' THEN 'Analyst'::userrole_new
                ELSE 'Viewer'::userrole_new
            END
        );
    """)
    
    # Drop old enum
    op.execute("DROP TYPE userrole;")
    
    # Rename new enum to original name
    op.execute("ALTER TYPE userrole_new RENAME TO userrole;")


def downgrade() -> None:
    # Create old enum type
    op.execute("""
        CREATE TYPE userrole_old AS ENUM (
            'ADMIN', 'REVIEWER', 'UPLOADER', 'VIEWER', 'COMPLIANCE',
            'Manager', 'Analyst'
        );
    """)
    
    # Revert users table
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role TYPE userrole_old 
        USING (
            CASE role::text
                WHEN 'Admin' THEN 'ADMIN'::userrole_old
                WHEN 'Reviewer' THEN 'REVIEWER'::userrole_old
                WHEN 'Uploader' THEN 'UPLOADER'::userrole_old
                WHEN 'Viewer' THEN 'VIEWER'::userrole_old
                WHEN 'Compliance' THEN 'COMPLIANCE'::userrole_old
                WHEN 'Manager' THEN 'Manager'::userrole_old
                WHEN 'Analyst' THEN 'Analyst'::userrole_old
                ELSE 'VIEWER'::userrole_old
            END
        );
    """)
    
    # Drop new enum
    op.execute("DROP TYPE userrole;")
    
    # Rename old enum back
    op.execute("ALTER TYPE userrole_old RENAME TO userrole;")

