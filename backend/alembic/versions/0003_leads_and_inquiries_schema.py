"""Leads and inquiries schema: builder_projects, lead_sequences, leads, lead_activities, website_inquiries

Revision ID: 0003_leads_and_inquiries
Revises: 0002_settings_and_audit
Create Date: 2026-11-23 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003_leads_and_inquiries'
down_revision: Union[str, None] = '0002_settings_and_audit'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # 1. builder_projects
    op.create_table(
        'builder_projects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('developer_name', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), server_default='Alwar', nullable=False),
        sa.Column('locality', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # 2. lead_sequences
    op.create_table(
        'lead_sequences',
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('last_sequence', sa.Integer(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('year'),
    )

    # 3. leads
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.String(length=32), nullable=False),
        sa.Column('idempotency_key', sa.String(length=64), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('mobile', sa.String(length=15), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('lead_type', sa.String(length=32), server_default='BUYER', nullable=False),
        sa.Column('source', sa.String(length=64), server_default='MANUAL', nullable=False),
        sa.Column('related_listing_id', sa.String(length=64), nullable=True),
        sa.Column('related_project_id', sa.Integer(), nullable=True),
        sa.Column('assigned_to', sa.String(length=32), nullable=True),
        sa.Column('stage', sa.String(length=32), server_default='NEW', nullable=False),
        sa.Column('temperature', sa.String(length=16), nullable=True),
        sa.Column('budget_min', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('budget_max', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('preferred_city', sa.String(length=100), server_default='Alwar', nullable=True),
        sa.Column('preferred_locality', sa.String(length=100), nullable=True),
        sa.Column('untouched_timer_start', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('is_untouched', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_duplicate', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_test', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['assigned_to'], ['employees.employee_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['related_project_id'], ['builder_projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_leads_lead_id'), 'leads', ['lead_id'], unique=True)
    op.create_index(op.f('ix_leads_idempotency_key'), 'leads', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_leads_mobile'), 'leads', ['mobile'], unique=False)
    op.create_index(op.f('ix_leads_assigned_to'), 'leads', ['assigned_to'], unique=False)
    op.create_index(op.f('ix_leads_stage'), 'leads', ['stage'], unique=False)
    op.create_index(op.f('ix_leads_created_at'), 'leads', ['created_at'], unique=False)

    # 4. lead_activities
    op.create_table(
        'lead_activities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lead_id', sa.String(length=32), nullable=False),
        sa.Column('action_type', sa.String(length=32), nullable=False),
        sa.Column('outcome', sa.String(length=64), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('next_action', sa.String(length=255), nullable=True),
        sa.Column('follow_up_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('logged_by', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.lead_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['logged_by'], ['employees.employee_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_lead_activities_lead_id'), 'lead_activities', ['lead_id'], unique=False)

    # 5. website_inquiries
    op.create_table(
        'website_inquiries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('inquiry_type', sa.String(length=32), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('mobile', sa.String(length=15), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('details', json_type, nullable=True),
        sa.Column('is_converted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('converted_lead_id', sa.String(length=32), nullable=True),
        sa.Column('converted_by_emp_id', sa.String(length=32), nullable=True),
        sa.Column('converted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['converted_by_emp_id'], ['employees.employee_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['converted_lead_id'], ['leads.lead_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_website_inquiries_inquiry_type'), 'website_inquiries', ['inquiry_type'], unique=False)
    op.create_index(op.f('ix_website_inquiries_mobile'), 'website_inquiries', ['mobile'], unique=False)
    op.create_index(op.f('ix_website_inquiries_is_converted'), 'website_inquiries', ['is_converted'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_website_inquiries_is_converted'), table_name='website_inquiries')
    op.drop_index(op.f('ix_website_inquiries_mobile'), table_name='website_inquiries')
    op.drop_index(op.f('ix_website_inquiries_inquiry_type'), table_name='website_inquiries')
    op.drop_table('website_inquiries')

    op.drop_index(op.f('ix_lead_activities_lead_id'), table_name='lead_activities')
    op.drop_table('lead_activities')

    op.drop_index(op.f('ix_leads_created_at'), table_name='leads')
    op.drop_index(op.f('ix_leads_stage'), table_name='leads')
    op.drop_index(op.f('ix_leads_assigned_to'), table_name='leads')
    op.drop_index(op.f('ix_leads_mobile'), table_name='leads')
    op.drop_index(op.f('ix_leads_idempotency_key'), table_name='leads')
    op.drop_index(op.f('ix_leads_lead_id'), table_name='leads')
    op.drop_table('leads')

    op.drop_table('lead_sequences')
    op.drop_table('builder_projects')
