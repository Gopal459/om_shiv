"""Universal soft delete deleted_at columns

Revision ID: 0010_add_soft_delete
Revises: 0009_owner_requests_schema
Create Date: 2026-11-23 18:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0010_add_soft_delete"
down_revision: Union[str, None] = "0009_owner_requests_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    "departments",
    "roles",
    "employees",
    "leads",
    "properties",
    "property_master_groups",
    "property_master_options",
    "pincode_master",
    "website_inquiries",
    "builder_projects",
    "owner_ad_requests",
    "system_settings",
]


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "deleted_at")
