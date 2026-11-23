"""Property verification schema: assignments, calls, documents

Revision ID: 0008_property_verification_schema
Revises: 0007_properties_schema
Create Date: 2026-11-23 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0008_property_verification_schema"
down_revision: Union[str, None] = "0007_properties_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "property_verification_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("assigned_to", sa.String(length=32), nullable=False),
        sa.Column("assigned_by", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prop_verify_assign_prop_id", "property_verification_assignments", ["property_id"], unique=False)

    op.create_table(
        "property_verification_calls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("caller_emp_id", sa.String(length=32), nullable=False),
        sa.Column("call_outcome", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("confirmed_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("scheduled_visit_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prop_verify_calls_prop_id", "property_verification_calls", ["property_id"], unique=False)

    op.create_table(
        "property_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=False),
        sa.Column("doc_type", sa.String(length=64), nullable=False),
        sa.Column("file_url", sa.String(length=500), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("uploaded_by", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prop_docs_prop_id", "property_documents", ["property_id"], unique=False)


def downgrade() -> None:
    op.drop_table("property_documents")
    op.drop_table("property_verification_calls")
    op.drop_table("property_verification_assignments")
