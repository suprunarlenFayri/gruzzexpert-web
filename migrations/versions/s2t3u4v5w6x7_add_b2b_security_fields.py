"""Add b2b security fields and support tables

Revision ID: s2t3u4v5w6x7
Revises: r1s2t3u4v5w6
Create Date: 2026-05-28 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 's2t3u4v5w6x7'
down_revision = 'r1s2t3u4v5w6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('balance', sa.Float(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('is_frozen', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('frozen_until', sa.DateTime(), nullable=True))

    op.create_table(
        'pending_login_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('attempt_token', sa.String(length=64), nullable=False),
        sa.Column('device_hash', sa.String(length=128), nullable=False),
        sa.Column('browser', sa.String(length=120), nullable=True),
        sa.Column('os', sa.String(length=120), nullable=True),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('sms_code', sa.String(length=10), nullable=True),
        sa.Column('email_code', sa.String(length=10), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('attempt_token'),
    )
    op.create_index('ix_pending_login_attempts_user_id', 'pending_login_attempts', ['user_id'])
    op.create_index('ix_pending_login_attempts_status', 'pending_login_attempts', ['status'])

    op.create_table(
        'phone_recovery_tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('old_phone', sa.String(length=20), nullable=True),
        sa.Column('new_phone', sa.String(length=20), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('workspace_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_phone_recovery_tickets_user_id', 'phone_recovery_tickets', ['user_id'])
    op.create_index('ix_phone_recovery_tickets_status', 'phone_recovery_tickets', ['status'])


def downgrade():
    op.drop_table('phone_recovery_tickets')
    op.drop_table('pending_login_attempts')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('frozen_until')
        batch_op.drop_column('is_frozen')
        batch_op.drop_column('balance')
