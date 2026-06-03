"""add contacts table

Revision ID: v6w7x8y9z0a1
Revises: u4v5w6x7y8z9
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa


revision = 'v6w7x8y9z0a1'
down_revision = 'u4v5w6x7y8z9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('contact_user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['contact_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'contact_user_id', name='unique_user_contact'),
    )
    op.create_index(op.f('ix_contacts_created_at'), 'contacts', ['created_at'], unique=False)
    op.create_index(op.f('ix_contacts_owner_id'), 'contacts', ['owner_id'], unique=False)
    op.create_index(op.f('ix_contacts_contact_user_id'), 'contacts', ['contact_user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_contacts_contact_user_id'), table_name='contacts')
    op.drop_index(op.f('ix_contacts_owner_id'), table_name='contacts')
    op.drop_index(op.f('ix_contacts_created_at'), table_name='contacts')
    op.drop_table('contacts')
