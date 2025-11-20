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
    # Add profile fields to users table (idempotent)
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image_url VARCHAR(500)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(50)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT")


def downgrade() -> None:
    # Remove profile fields from users table
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS bio")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS phone")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS profile_image_url")
