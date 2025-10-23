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
    # Add organization fields
    op.add_column('organizations', sa.Column('logo_url', sa.String(length=500), nullable=True))
    op.add_column('organizations', sa.Column('website', sa.String(length=200), nullable=True))
    op.add_column('organizations', sa.Column('company_size', sa.String(length=50), nullable=True))
    op.add_column('organizations', sa.Column('industry', sa.String(length=100), nullable=True))
    op.add_column('organizations', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove organization fields
    op.drop_column('organizations', 'description')
    op.drop_column('organizations', 'industry')
    op.drop_column('organizations', 'company_size')
    op.drop_column('organizations', 'website')
    op.drop_column('organizations', 'logo_url')
