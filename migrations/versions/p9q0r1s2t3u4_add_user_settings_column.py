"""Add user settings JSON column

Revision ID: p9q0r1s2t3u4
Revises: o3p4q5r6s7t8
Create Date: 2026-05-27 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'p9q0r1s2t3u4'
down_revision = 'o3p4q5r6s7t8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('settings', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('settings')
