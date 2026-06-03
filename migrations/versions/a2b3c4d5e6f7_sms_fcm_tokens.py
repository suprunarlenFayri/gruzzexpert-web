"""SMS verification codes and FCM device tokens

Revision ID: a2b3c4d5e6f7
Revises: z1a2b3c4d5e6
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa


revision = 'a2b3c4d5e6f7'
down_revision = 'z1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'sms_verification_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('purpose', sa.String(length=20), nullable=False),
        sa.Column('session_token', sa.String(length=64), nullable=False),
        sa.Column('code_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('consumed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sms_verification_codes_phone', 'sms_verification_codes', ['phone'])
    op.create_index(
        'ix_sms_verification_codes_session_token',
        'sms_verification_codes',
        ['session_token'],
        unique=True,
    )

    op.create_table(
        'user_fcm_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=512), nullable=False),
        sa.Column('platform', sa.String(length=20), nullable=True),
        sa.Column('device_name', sa.String(length=120), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index('ix_user_fcm_tokens_user_id', 'user_fcm_tokens', ['user_id'])


def downgrade():
    op.drop_table('user_fcm_tokens')
    op.drop_table('sms_verification_codes')
