"""Add is_on_leave column to employees

Revision ID: 0005_employee_leave
Revises: 0004_lead_pipeline_and_actions
Create Date: 2026-11-23 16:55:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_employee_leave"
down_revision = "0004_lead_pipeline_and_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "employees",
        sa.Column("is_on_leave", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("employees", "is_on_leave")
