"""Property master options and pincode master schema

Revision ID: 0006_property_master
Revises: 0005_employee_leave
Create Date: 2026-11-23 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006_property_master"
down_revision: Union[str, None] = "0005_employee_leave"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.create_table(
        "property_master_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_property_master_groups_code", "property_master_groups", ["code"], unique=True)

    op.create_table(
        "property_master_options",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("applicable_categories", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["property_master_groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "code", name="uq_master_group_option_code"),
    )
    op.create_index("ix_property_master_options_group_id", "property_master_options", ["group_id"], unique=False)

    op.create_table(
        "pincode_master",
        sa.Column("pincode", sa.String(length=6), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("is_serviceable", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("pincode"),
    )
    op.create_index("ix_pincode_master_city", "pincode_master", ["city"], unique=False)
    op.create_index("ix_pincode_master_pincode", "pincode_master", ["pincode"], unique=True)


def downgrade() -> None:
    op.drop_table("pincode_master")
    op.drop_table("property_master_options")
    op.drop_table("property_master_groups")
