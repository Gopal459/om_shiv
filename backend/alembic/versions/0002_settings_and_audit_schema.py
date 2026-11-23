"""Settings engine and audit logs schema: system_settings, audit_logs

Revision ID: 0002_settings_and_audit
Revises: 0001_initial_identity
Create Date: 2026-11-23 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002_settings_and_audit'
down_revision: Union[str, None] = '0001_initial_identity'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # 1. system_settings
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', json_type, nullable=False),
        sa.Column('data_type', sa.String(length=32), server_default='STRING', nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_by', sa.String(length=32), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['updated_by'], ['employees.employee_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('key'),
    )
    op.create_index(op.f('ix_system_settings_category'), 'system_settings', ['category'], unique=False)

    # 2. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('entity_name', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('old_state', json_type, nullable=True),
        sa.Column('new_state', json_type, nullable=True),
        sa.Column('performed_by', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_entity_name'), 'audit_logs', ['entity_name'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity_id'), 'audit_logs', ['entity_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_performed_by'), 'audit_logs', ['performed_by'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_timestamp'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_performed_by'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_entity_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_entity_name'), table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_index(op.f('ix_system_settings_category'), table_name='system_settings')
    op.drop_table('system_settings')
