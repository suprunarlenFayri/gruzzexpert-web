"""contacts social: blacklist, chat/message pins, hide chat

Revision ID: x8y9z0a1b2c3
Revises: w7x8y9z0a1b2
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa


revision = 'x8y9z0a1b2c3'
down_revision = 'w7x8y9z0a1b2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('chat_participants', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('is_hidden', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('pinned_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('pinned_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('deleted_for_all', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        'message_hidden',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'message_id', name='unique_message_hidden'),
    )
    op.create_index('ix_message_hidden_user_id', 'message_hidden', ['user_id'], unique=False)
    op.create_index('ix_message_hidden_message_id', 'message_hidden', ['message_id'], unique=False)

    op.create_table(
        'blacklist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('blocked_user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['blocked_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'blocked_user_id', name='unique_blacklist_entry'),
    )
    op.create_index('ix_blacklist_owner_id', 'blacklist', ['owner_id'], unique=False)


def downgrade():
    op.drop_index('ix_blacklist_owner_id', table_name='blacklist')
    op.drop_table('blacklist')
    op.drop_index('ix_message_hidden_message_id', table_name='message_hidden')
    op.drop_index('ix_message_hidden_user_id', table_name='message_hidden')
    op.drop_table('message_hidden')

    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_column('deleted_for_all')
        batch_op.drop_column('pinned_at')
        batch_op.drop_column('is_pinned')

    with op.batch_alter_table('chat_participants', schema=None) as batch_op:
        batch_op.drop_column('pinned_at')
        batch_op.drop_column('is_hidden')
        batch_op.drop_column('is_pinned')
