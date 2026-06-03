"""Add status field to clients

Revision ID: u4v5w6x7y8z9
Revises: t3u4v5w6x7y8
Create Date: 2026-05-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'u4v5w6x7y8z9'
down_revision = 't3u4v5w6x7y8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('status', sa.String(length=20), nullable=False, server_default='active')
        )
        batch_op.create_index('ix_clients_status', ['status'], unique=False)


def downgrade():
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.drop_index('ix_clients_status')
        batch_op.drop_column('status')
