"""merge_multiple_heads

Revision ID: f42f49bda1a1
Revises: 001_org_connections, 59ad7a332a1f
Create Date: 2025-11-20 13:39:55.929331

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f42f49bda1a1'
down_revision = ('001_org_connections', '59ad7a332a1f')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
