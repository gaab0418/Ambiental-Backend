"""add_user_organization_many_to_many

Revision ID: bbbb58c5cb60
Revises: 0197ec68a823
Create Date: 2025-10-26 09:46:30.924915

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bbbb58c5cb60'
down_revision = '0197ec68a823'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the user_organization_association table
    op.create_table(
        'user_organization_association',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'organization_id')
    )
    
    # Create indexes for better query performance
    op.create_index('ix_user_org_assoc_user_id', 'user_organization_association', ['user_id'])
    op.create_index('ix_user_org_assoc_org_id', 'user_organization_association', ['organization_id'])
    
    # Migrate existing data from users table to association table
    # This preserves the current user-organization relationships
    op.execute("""
        INSERT INTO user_organization_association (user_id, organization_id, role_id, created_at)
        SELECT id, organization_id, role_id, created_at
        FROM users
        WHERE organization_id IS NOT NULL
    """)
    
    # Remove role_id from users table (now in association table)
    op.drop_constraint('users_role_id_fkey', 'users', type_='foreignkey')
    op.drop_column('users', 'role_id')
    
    # Remove organization_id from users table (now in association table)
    op.drop_constraint('users_organization_id_fkey', 'users', type_='foreignkey')
    op.drop_index('ix_users_organization_id', table_name='users')
    op.drop_column('users', 'organization_id')


def downgrade() -> None:
    # Add back organization_id to users table
    op.add_column('users', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.create_index('ix_users_organization_id', 'users', ['organization_id'])
    op.create_foreign_key('users_organization_id_fkey', 'users', 'organizations', ['organization_id'], ['id'])
    
    # Add back role_id to users table
    op.add_column('users', sa.Column('role_id', sa.Integer(), nullable=True))
    op.create_foreign_key('users_role_id_fkey', 'users', 'roles', ['role_id'], ['id'])
    
    # Migrate data back - use the first organization association for each user
    op.execute("""
        UPDATE users
        SET organization_id = (
            SELECT organization_id
            FROM user_organization_association
            WHERE user_organization_association.user_id = users.id
            LIMIT 1
        ),
        role_id = (
            SELECT role_id
            FROM user_organization_association
            WHERE user_organization_association.user_id = users.id
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1
            FROM user_organization_association
            WHERE user_organization_association.user_id = users.id
        )
    """)
    
    # Drop the association table
    op.drop_index('ix_user_org_assoc_org_id', table_name='user_organization_association')
    op.drop_index('ix_user_org_assoc_user_id', table_name='user_organization_association')
    op.drop_table('user_organization_association')
