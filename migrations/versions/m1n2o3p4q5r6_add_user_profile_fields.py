"""Add birth_date and bank_card to users

Revision ID: m1n2o3p4q5r6
Revises: l1m2n3o4p5q6
Create Date: 2026-05-27 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'm1n2o3p4q5r6'
down_revision = 'l1m2n3o4p5q6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('birth_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('bank_card', sa.String(length=30), nullable=True))

    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE users
        SET birth_date = (
            SELECT vr.birth_date
            FROM verification_requests vr
            WHERE vr.user_id = users.id AND vr.status = 'approved'
            ORDER BY vr.moderated_at DESC
            LIMIT 1
        )
        WHERE birth_date IS NULL
    """))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('bank_card')
        batch_op.drop_column('birth_date')
