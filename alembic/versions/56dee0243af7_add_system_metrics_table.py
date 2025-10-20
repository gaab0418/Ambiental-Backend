"""add_system_metrics_table

Revision ID: 56dee0243af7
Revises: e6bc440ca310
Create Date: 2025-10-13 22:18:19.612898

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '56dee0243af7'
down_revision = 'e6bc440ca310'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create system_metrics table
    op.create_table('system_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_type', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_metrics_id'), 'system_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_system_metrics_metric_type'), 'system_metrics', ['metric_type'], unique=False)
    op.create_index(op.f('ix_system_metrics_recorded_at'), 'system_metrics', ['recorded_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_system_metrics_recorded_at'), table_name='system_metrics')
    op.drop_index(op.f('ix_system_metrics_metric_type'), table_name='system_metrics')
    op.drop_index(op.f('ix_system_metrics_id'), table_name='system_metrics')
    op.drop_table('system_metrics')
