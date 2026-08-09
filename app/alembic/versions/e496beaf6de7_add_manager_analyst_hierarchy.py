"""add_manager_analyst_hierarchy

Revision ID: e496beaf6de7
Revises: add_search_indexes
Create Date: 2025-10-03 02:20:16.639836+00:00

"""
from alembic import op, context
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e496beaf6de7'
down_revision = 'add_search_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new roles to enum, regardless of whether the enum is named 'user_role' or 'userrole'
    with op.get_context().autocommit_block():
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
                    BEGIN
                        ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'Manager';
                    EXCEPTION WHEN duplicate_object THEN NULL; END;
                    BEGIN
                        ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'Analyst';
                    EXCEPTION WHEN duplicate_object THEN NULL; END;
                ELSIF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
                    BEGIN
                        ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'Manager';
                    EXCEPTION WHEN duplicate_object THEN NULL; END;
                    BEGIN
                        ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'Analyst';
                    EXCEPTION WHEN duplicate_object THEN NULL; END;
                END IF;
            END
            $$;
            """
        )
    
    # Add manager_id column for hierarchical relationships
    op.add_column('users', sa.Column('manager_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_users_manager_id'), 'users', ['manager_id'], unique=False)
    op.create_foreign_key('fk_users_manager_id', 'users', 'users', ['manager_id'], ['id'], ondelete='SET NULL')

    # Add manager_id to audit_logs for hierarchical audit queries
    op.add_column('audit_logs', sa.Column('manager_id', sa.Integer(), nullable=True))
    op.create_index('idx_audit_manager', 'audit_logs', ['manager_id'], unique=False)
    op.create_foreign_key('fk_audit_logs_manager_id', 'audit_logs', 'users', ['manager_id'], ['id'], ondelete='SET NULL')
    
    # Migrate existing roles to new hierarchy
    # Reviewer -> Manager, Uploader/Viewer -> Analyst
    op.execute("""
        UPDATE users 
        SET role = 'Manager'
        WHERE role::text = 'Reviewer'
    """)
    
    op.execute("""
        UPDATE users 
        SET role = 'Analyst'
        WHERE role::text IN ('Uploader', 'Viewer')
    """)


def downgrade() -> None:
    # Remove foreign key and column
    op.drop_constraint('fk_users_manager_id', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_manager_id'), table_name='users')
    op.drop_column('users', 'manager_id')

    # Remove audit_logs manager linkage
    op.drop_constraint('fk_audit_logs_manager_id', 'audit_logs', type_='foreignkey')
    op.drop_index('idx_audit_manager', table_name='audit_logs')
    op.drop_column('audit_logs', 'manager_id')
    
    # Revert role changes
    op.execute("""
        UPDATE users 
        SET role = 'Reviewer'
        WHERE role = 'Manager'
    """)
    
    op.execute("""
        UPDATE users 
        SET role = 'Viewer'
        WHERE role = 'Analyst'
    """)