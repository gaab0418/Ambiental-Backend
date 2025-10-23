"""add_document_templates_table

Revision ID: 8ff0183c141e
Revises: 56dee0243af7
Create Date: 2025-10-13 22:18:25.788182

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8ff0183c141e'
down_revision = '56dee0243af7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create document_templates table
    op.create_table('document_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('is_global', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_templates_id'), 'document_templates', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_document_templates_id'), table_name='document_templates')
    op.drop_table('document_templates')
