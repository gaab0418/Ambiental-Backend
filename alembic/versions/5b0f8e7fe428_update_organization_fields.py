"""update_organization_fields

Revision ID: 5b0f8e7fe428
Revises: 41e7e2a63f07
Create Date: 2025-10-13 22:18:38.353487

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b0f8e7fe428'
down_revision = '41e7e2a63f07'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add organization fields (idempotent)
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500)")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS website VARCHAR(200)")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS company_size VARCHAR(50)")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS industry VARCHAR(100)")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS description TEXT")


def downgrade() -> None:
    # Remove organization fields
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS description")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS industry")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS company_size")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS website")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS logo_url")
