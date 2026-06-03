"""Add user_devices for trusted device fingerprinting

Revision ID: r1s2t3u4v5w6
Revises: q0r1s2t3u4v5
Create Date: 2026-05-28 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'r1s2t3u4v5w6'
down_revision = 'q0r1s2t3u4v5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('device_hash', sa.String(length=128), nullable=False),
        sa.Column('browser', sa.String(length=120), nullable=True),
        sa.Column('os', sa.String(length=120), nullable=True),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('is_trusted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'device_hash', name='unique_user_device'),
    )
    with op.batch_alter_table('user_devices', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_devices_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_user_devices_device_hash'), ['device_hash'], unique=False)
        batch_op.create_index('idx_user_devices_user_trusted', ['user_id', 'is_trusted'], unique=False)


def downgrade():
    op.drop_table('user_devices')
