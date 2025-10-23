"""add_chat_tables

Revision ID: 0197ec68a823
Revises: c5d0b5daa81e
Create Date: 2025-10-20 21:01:28.327727

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0197ec68a823'
down_revision = 'c5d0b5daa81e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create chat_threads table
    op.create_table(
        'chat_threads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_threads_created_at'), 'chat_threads', ['created_at'], unique=False)
    op.create_index(op.f('ix_chat_threads_id'), 'chat_threads', ['id'], unique=False)
    op.create_index(op.f('ix_chat_threads_organization_id'), 'chat_threads', ['organization_id'], unique=False)
    op.create_index(op.f('ix_chat_threads_user_id'), 'chat_threads', ['user_id'], unique=False)
    
    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Enum('USER', 'ASSISTANT', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_messages_created_at'), 'chat_messages', ['created_at'], unique=False)
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)
    op.create_index(op.f('ix_chat_messages_thread_id'), 'chat_messages', ['thread_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_chat_messages_thread_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_created_at'), table_name='chat_messages')
    op.drop_table('chat_messages')
    
    op.drop_index(op.f('ix_chat_threads_user_id'), table_name='chat_threads')
    op.drop_index(op.f('ix_chat_threads_organization_id'), table_name='chat_threads')
    op.drop_index(op.f('ix_chat_threads_id'), table_name='chat_threads')
    op.drop_index(op.f('ix_chat_threads_created_at'), table_name='chat_threads')
    op.drop_table('chat_threads')
