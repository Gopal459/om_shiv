"""Lead pipeline and actions schema updates: follow_up_date, last_contacted_at, lost_reason on leads, and stage/performer tracking on lead_activities

Revision ID: 0004_lead_pipeline_and_actions
Revises: 0003_leads_and_inquiries
Create Date: 2026-11-23 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_lead_pipeline_and_actions'
down_revision: Union[str, None] = '0003_leads_and_inquiries'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add follow_up_date, last_contacted_at, lost_reason to leads table
    op.add_column('leads', sa.Column('follow_up_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('leads', sa.Column('last_contacted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('leads', sa.Column('lost_reason', sa.Text(), nullable=True))
    op.create_index(op.f('ix_leads_follow_up_date'), 'leads', ['follow_up_date'], unique=False)

    # 2. Add stage_before, stage_after, temperature, performed_by to lead_activities table
    op.add_column('lead_activities', sa.Column('stage_before', sa.String(length=32), nullable=True))
    op.add_column('lead_activities', sa.Column('stage_after', sa.String(length=32), nullable=True))
    op.add_column('lead_activities', sa.Column('temperature', sa.String(length=16), nullable=True))
    op.add_column('lead_activities', sa.Column('performed_by', sa.String(length=32), nullable=True))
    op.create_foreign_key(
        'fk_lead_activities_performed_by',
        'lead_activities',
        'employees',
        ['performed_by'],
        ['employee_id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_lead_activities_performed_by', 'lead_activities', type_='foreignkey')
    op.drop_column('lead_activities', 'performed_by')
    op.drop_column('lead_activities', 'temperature')
    op.drop_column('lead_activities', 'stage_after')
    op.drop_column('lead_activities', 'stage_before')

    op.drop_index(op.f('ix_leads_follow_up_date'), table_name='leads')
    op.drop_column('leads', 'lost_reason')
    op.drop_column('leads', 'last_contacted_at')
    op.drop_column('leads', 'follow_up_date')
