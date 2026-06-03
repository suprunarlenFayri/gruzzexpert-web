"""profile privacy fields and user sessions table

Revision ID: w7x8y9z0a1b2
Revises: v6w7x8y9z0a1
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa


revision = 'w7x8y9z0a1b2'
down_revision = 'v6w7x8y9z0a1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=50), nullable=True))
        batch_op.add_column(
            sa.Column('send_by_enter', sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        batch_op.add_column(
            sa.Column('phone_privacy', sa.String(length=20), nullable=False, server_default='contacts'),
        )
        batch_op.create_index('ix_users_username', ['username'], unique=True)

    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('device_name', sa.String(length=200), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('last_active', sa.DateTime(), nullable=True),
        sa.Column('token', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_sessions_created_at', 'user_sessions', ['created_at'], unique=False)
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'], unique=False)
    op.create_index('ix_user_sessions_token', 'user_sessions', ['token'], unique=False)


def downgrade():
    op.drop_index('ix_user_sessions_token', table_name='user_sessions')
    op.drop_index('ix_user_sessions_user_id', table_name='user_sessions')
    op.drop_index('ix_user_sessions_created_at', table_name='user_sessions')
    op.drop_table('user_sessions')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index('ix_users_username')
        batch_op.drop_column('phone_privacy')
        batch_op.drop_column('send_by_enter')
        batch_op.drop_column('username')
