"""Ensure users table has last_login_at field

Revision ID: 9f787ba2a678
Revises: 7297349ace40
Create Date: 2025-10-13 21:50:33.489274

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f787ba2a678'
down_revision = '7297349ace40'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add last_login_at column to users table if it doesn't exist
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    users_columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'last_login_at' not in users_columns:
        op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove last_login_at column from users table
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    users_columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'last_login_at' in users_columns:
        op.drop_column('users', 'last_login_at')
