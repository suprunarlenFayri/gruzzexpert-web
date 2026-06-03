"""Worker application legal consent fields

Revision ID: t3u4v5w6x7y8
Revises: s2t3u4v5w6x7
Create Date: 2026-05-28 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 't3u4v5w6x7y8'
down_revision = 's2t3u4v5w6x7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('verification_requests', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_legal_agreed', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('agreed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('agreed_from_ip', sa.String(length=45), nullable=True))


def downgrade():
    with op.batch_alter_table('verification_requests', schema=None) as batch_op:
        batch_op.drop_column('agreed_from_ip')
        batch_op.drop_column('agreed_at')
        batch_op.drop_column('is_legal_agreed')
