"""update_user_profile_fields

Revision ID: 41e7e2a63f07
Revises: 8ff0183c141e
Create Date: 2025-10-13 22:18:32.278902

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '41e7e2a63f07'
down_revision = '8ff0183c141e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add profile fields to users table
    op.add_column('users', sa.Column('profile_image_url', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('bio', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove profile fields from users table
    op.drop_column('users', 'bio')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'profile_image_url')
