"""add_last_organization_id_to_users

Revision ID: a1b2c3d4e5f6
Revises: bbbb58c5cb60
Create Date: 2025-01-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'bbbb58c5cb60'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add last_organization_id column to users table
    op.add_column('users', sa.Column('last_organization_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'users_last_organization_id_fkey',
        'users',
        'organizations',
        ['last_organization_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for better query performance
    op.create_index('ix_users_last_organization_id', 'users', ['last_organization_id'])


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_users_last_organization_id', table_name='users')
    
    # Drop foreign key constraint
    op.drop_constraint('users_last_organization_id_fkey', 'users', type_='foreignkey')
    
    # Drop column
    op.drop_column('users', 'last_organization_id')

