"""Properties master and child subcategory schema

Revision ID: 0007_properties_schema
Revises: 0006_property_master
Create Date: 2026-11-23 17:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0007_properties_schema"
down_revision: Union[str, None] = "0006_property_master"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "property_sequences",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("year"),
    )

    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.String(length=32), nullable=False),
        sa.Column("listing_type", sa.Integer(), nullable=False),
        sa.Column("category_code", sa.Integer(), nullable=False),
        sa.Column("sub_category_code", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pincode", sa.String(length=6), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("locality", sa.String(length=150), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("expected_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("price_negotiable", sa.Boolean(), nullable=False),
        sa.Column("owner_name", sa.String(length=150), nullable=False),
        sa.Column("owner_mobile", sa.String(length=15), nullable=False),
        sa.Column("posted_by_role", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("verified_status", sa.Integer(), nullable=False),
        sa.Column("is_live", sa.Boolean(), nullable=False),
        sa.Column("is_recycled", sa.Boolean(), nullable=False),
        sa.Column("recycled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["pincode"], ["pincode_master.pincode"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_properties_pincode", "properties", ["pincode"], unique=False)
    op.create_index("ix_properties_property_id", "properties", ["property_id"], unique=True)

    op.create_table(
        "prop_residential_flats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("bhk", sa.Integer(), nullable=False),
        sa.Column("rooms", sa.Integer(), nullable=False),
        sa.Column("bathrooms", sa.Integer(), nullable=False),
        sa.Column("balconies", sa.Integer(), nullable=False),
        sa.Column("super_area", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("carpet_area", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("total_floors", sa.Integer(), nullable=False),
        sa.Column("property_floor", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id"),
    )

    op.create_table(
        "prop_houses_villas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("bhk", sa.Integer(), nullable=False),
        sa.Column("rooms", sa.Integer(), nullable=False),
        sa.Column("bathrooms", sa.Integer(), nullable=False),
        sa.Column("total_floors", sa.Integer(), nullable=False),
        sa.Column("sell_part_code", sa.String(length=50), nullable=True),
        sa.Column("plot_area", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("built_up_area", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id"),
    )

    op.create_table(
        "prop_pg",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("pg_name", sa.String(length=150), nullable=False),
        sa.Column("available_for", sa.String(length=50), nullable=False),
        sa.Column("room_type", sa.String(length=50), nullable=False),
        sa.Column("food_included", sa.Boolean(), nullable=False),
        sa.Column("attached_bathroom", sa.Boolean(), nullable=False),
        sa.Column("attached_balcony", sa.Boolean(), nullable=False),
        sa.Column("common_area", sa.Boolean(), nullable=False),
        sa.Column("smoking_allowed", sa.Boolean(), nullable=False),
        sa.Column("alcohol_allowed", sa.Boolean(), nullable=False),
        sa.Column("rent_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("rent_negotiable", sa.Boolean(), nullable=False),
        sa.Column("extra_charges", sa.String(length=255), nullable=True),
        sa.Column("min_stay_months", sa.Integer(), nullable=False),
        sa.Column("notice_period_days", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id"),
    )


def downgrade() -> None:
    op.drop_table("prop_pg")
    op.drop_table("prop_houses_villas")
    op.drop_table("prop_residential_flats")
    op.drop_table("properties")
    op.drop_table("property_sequences")
