"""add_consultant_role

Revision ID: c5d0b5daa81e
Revises: 4578e264a50b
Create Date: 2025-10-13 22:18:58.469904

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5d0b5daa81e'
down_revision = '4578e264a50b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add CONSULTANT role
    op.execute("""
        INSERT INTO roles (name, display_name, description, permissions, is_system, created_at, updated_at)
        VALUES (
            'CONSULTANT',
            'Consultor',
            'Consultor de negócio com acesso a múltiplas organizações e criação de templates',
            '{"can_view_organizations": true, "can_edit_organization_data": true, "can_create_templates": true, "can_create_global_templates": true, "can_manage_users": false, "can_manage_subscriptions": false}',
            false,
            NOW(),
            NOW()
        )
    """)


def downgrade() -> None:
    # Remove CONSULTANT role
    op.execute("DELETE FROM roles WHERE name = 'CONSULTANT'")
