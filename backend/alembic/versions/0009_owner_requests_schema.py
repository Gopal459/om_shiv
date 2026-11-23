"""Owner requests schema

Revision ID: 0009_owner_requests_schema
Revises: 0008_property_verification_schema
Create Date: 2026-11-23 17:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0009_owner_requests_schema"
down_revision: Union[str, None] = "0008_property_verification_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "owner_ad_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("request_type", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_by_mobile", sa.String(length=15), nullable=False),
        sa.Column("reviewed_by", sa.String(length=32), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_owner_ad_requests_property_id", "owner_ad_requests", ["property_id"], unique=False)
    op.create_index("ix_owner_ad_requests_status", "owner_ad_requests", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("owner_ad_requests")
