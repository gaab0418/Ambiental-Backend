"""add org connections table

Revision ID: 001_org_connections
Revises: 
Create Date: 2025-11-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_org_connections'
down_revision = 'e6bc440ca310'  # Last migration in the list
branch_labels = None
depends_on = None


def upgrade():
    # Add mode and activation_key_hash to organizations
    op.add_column('organizations', sa.Column('mode', sa.String(20), nullable=False, server_default='saas'))
    op.add_column('organizations', sa.Column('activation_key_hash', sa.String(255), nullable=True))
    op.add_column('organizations', sa.Column('status', sa.String(20), nullable=False, server_default='active'))
    
    # Create org_connections table for multi-tenant database routing
    op.create_table(
        'org_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('db_type', sa.String(50), nullable=False),  # app, vector, logs
        sa.Column('location', sa.String(20), nullable=False),  # cloud, on_prem
        sa.Column('host_encrypted', sa.Text(), nullable=True),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('database_name_encrypted', sa.Text(), nullable=True),
        sa.Column('username_encrypted', sa.Text(), nullable=True),
        sa.Column('password_encrypted', sa.Text(), nullable=True),
        sa.Column('connection_string_encrypted', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_org_connections_org_id', 'org_connections', ['org_id'])
    op.create_index('ix_org_connections_db_type', 'org_connections', ['db_type'])
    
    # Create municipal_instructions table for IN management
    op.create_table(
        'municipal_instructions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('municipality', sa.String(100), nullable=False),
        sa.Column('state', sa.String(2), nullable=False),
        sa.Column('instruction_number', sa.String(50), nullable=False),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('content_text', sa.Text(), nullable=True),
        sa.Column('content_url', sa.String(500), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_municipal_instructions_municipality', 'municipal_instructions', ['municipality', 'state'])
    op.create_index('ix_municipal_instructions_current', 'municipal_instructions', ['is_current'])
    
    # Create process_files table (if not exists from chat_files)
    # Extending existing chat_files functionality
    op.add_column('chat_files', sa.Column('file_hash', sa.String(64), nullable=True))
    op.add_column('chat_files', sa.Column('file_version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('chat_files', sa.Column('category', sa.String(100), nullable=True))
    op.add_column('chat_files', sa.Column('status', sa.String(50), nullable=False, server_default='uploaded'))
    op.add_column('chat_files', sa.Column('metadata_json', postgresql.JSONB(), nullable=True))
    op.add_column('chat_files', sa.Column('vectorized_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create flow_metrics table for observability
    op.create_table(
        'flow_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('flow_name', sa.String(100), nullable=False),
        sa.Column('execution_id', sa.String(100), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_flow_metrics_org_id', 'flow_metrics', ['org_id'])
    op.create_index('ix_flow_metrics_flow_name', 'flow_metrics', ['flow_name'])
    op.create_index('ix_flow_metrics_created_at', 'flow_metrics', ['created_at'])


def downgrade():
    op.drop_index('ix_flow_metrics_created_at')
    op.drop_index('ix_flow_metrics_flow_name')
    op.drop_index('ix_flow_metrics_org_id')
    op.drop_table('flow_metrics')
    
    op.drop_column('chat_files', 'vectorized_at')
    op.drop_column('chat_files', 'metadata_json')
    op.drop_column('chat_files', 'status')
    op.drop_column('chat_files', 'category')
    op.drop_column('chat_files', 'file_version')
    op.drop_column('chat_files', 'file_hash')
    
    op.drop_index('ix_municipal_instructions_current')
    op.drop_index('ix_municipal_instructions_municipality')
    op.drop_table('municipal_instructions')
    
    op.drop_index('ix_org_connections_db_type')
    op.drop_index('ix_org_connections_org_id')
    op.drop_table('org_connections')
    
    op.drop_column('organizations', 'status')
    op.drop_column('organizations', 'activation_key_hash')
    op.drop_column('organizations', 'mode')



