"""rename_super_admin_to_administrator

Revision ID: 4578e264a50b
Revises: 5b0f8e7fe428
Create Date: 2025-10-13 22:18:51.408893

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4578e264a50b'
down_revision = '5b0f8e7fe428'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename SUPER_ADMIN to ADMINISTRATOR in roles table
    op.execute("UPDATE roles SET name = 'ADMINISTRATOR', display_name = 'Administrador' WHERE name = 'SUPER_ADMIN'")


def downgrade() -> None:
    # Rename ADMINISTRATOR back to SUPER_ADMIN
    op.execute("UPDATE roles SET name = 'SUPER_ADMIN', display_name = 'Super Administrador' WHERE name = 'ADMINISTRATOR'")
