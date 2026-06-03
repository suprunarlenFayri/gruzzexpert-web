"""Widen clients.phone for encrypted storage

Revision ID: y9z0a1b2c3d4
Revises: x8y9z0a1b2c3
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa


revision = 'y9z0a1b2c3d4'
down_revision = '25f00e4688ba'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.alter_column(
            'phone',
            existing_type=sa.String(length=20),
            type_=sa.String(length=512),
            existing_nullable=True,
        )


def downgrade():
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.alter_column(
            'phone',
            existing_type=sa.String(length=512),
            type_=sa.String(length=20),
            existing_nullable=True,
        )
