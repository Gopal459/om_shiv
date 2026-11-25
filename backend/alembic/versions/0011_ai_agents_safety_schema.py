"""AI agents safety schema: ai_agent_configs, customer_consents, ai_approval_queue, ai_agent_execution_logs, property_alert_history

Revision ID: 0011_ai_agents_safety_schema
Revises: 0010_add_soft_delete
Create Date: 2026-11-25 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0011_ai_agents_safety_schema"
down_revision: Union[str, None] = "0010_add_soft_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    # 1. ai_agent_configs
    op.create_table(
        "ai_agent_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("mode", sa.String(length=32), server_default="SHADOW", nullable=False),
        sa.Column("rate_limit_per_hour", sa.Integer(), server_default=sa.text("10"), nullable=False),
        sa.Column("requires_hitl", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_customer_facing", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("extra_config", json_type, server_default=sa.text("'{}'"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_agent_configs_agent_name"), "ai_agent_configs", ["agent_name"], unique=True)

    # 2. customer_consents
    op.create_table(
        "customer_consents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mobile", sa.String(length=15), nullable=False),
        sa.Column("channel", sa.String(length=32), server_default="WHATSAPP", nullable=False),
        sa.Column("is_opted_in", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("consent_source", sa.String(length=64), nullable=True),
        sa.Column("opted_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opted_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opt_out_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customer_consents_mobile"), "customer_consents", ["mobile"], unique=False)

    # 3. ai_approval_queue
    op.create_table(
        "ai_approval_queue",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column("lead_id", sa.String(length=32), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("proposed_payload", json_type, server_default=sa.text("'{}'"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=32), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_approval_queue_agent_name"), "ai_approval_queue", ["agent_name"], unique=False)
    op.create_index(op.f("ix_ai_approval_queue_lead_id"), "ai_approval_queue", ["lead_id"], unique=False)
    op.create_index(op.f("ix_ai_approval_queue_status"), "ai_approval_queue", ["status"], unique=False)

    # 4. ai_agent_execution_logs
    op.create_table(
        "ai_agent_execution_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column("lead_id", sa.String(length=32), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=True),
        sa.Column("mode", sa.String(length=32), server_default="SHADOW", nullable=False),
        sa.Column("trigger_event", sa.String(length=64), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_response", sa.Text(), nullable=True),
        sa.Column("tools_called", json_type, nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_agent_execution_logs_agent_name"), "ai_agent_execution_logs", ["agent_name"], unique=False)
    op.create_index(op.f("ix_ai_agent_execution_logs_lead_id"), "ai_agent_execution_logs", ["lead_id"], unique=False)
    op.create_index(op.f("ix_ai_agent_execution_logs_status"), "ai_agent_execution_logs", ["status"], unique=False)
    op.create_index(op.f("ix_ai_agent_execution_logs_approval_id"), "ai_agent_execution_logs", ["approval_id"], unique=False)
    op.create_index(op.f("ix_ai_agent_execution_logs_created_at"), "ai_agent_execution_logs", ["created_at"], unique=False)

    # 5. property_alert_history
    op.create_table(
        "property_alert_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lead_id", sa.String(length=32), nullable=False),
        sa.Column("property_id", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), server_default="WHATSAPP", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="SENT", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_property_alert_history_lead_id"), "property_alert_history", ["lead_id"], unique=False)
    op.create_index(op.f("ix_property_alert_history_property_id"), "property_alert_history", ["property_id"], unique=False)
    op.create_index(op.f("ix_property_alert_history_sent_at"), "property_alert_history", ["sent_at"], unique=False)


def downgrade() -> None:
    # Drop property_alert_history
    op.drop_index(op.f("ix_property_alert_history_sent_at"), table_name="property_alert_history")
    op.drop_index(op.f("ix_property_alert_history_property_id"), table_name="property_alert_history")
    op.drop_index(op.f("ix_property_alert_history_lead_id"), table_name="property_alert_history")
    op.drop_table("property_alert_history")

    # Drop ai_agent_execution_logs
    op.drop_index(op.f("ix_ai_agent_execution_logs_created_at"), table_name="ai_agent_execution_logs")
    op.drop_index(op.f("ix_ai_agent_execution_logs_approval_id"), table_name="ai_agent_execution_logs")
    op.drop_index(op.f("ix_ai_agent_execution_logs_status"), table_name="ai_agent_execution_logs")
    op.drop_index(op.f("ix_ai_agent_execution_logs_lead_id"), table_name="ai_agent_execution_logs")
    op.drop_index(op.f("ix_ai_agent_execution_logs_agent_name"), table_name="ai_agent_execution_logs")
    op.drop_table("ai_agent_execution_logs")

    # Drop ai_approval_queue
    op.drop_index(op.f("ix_ai_approval_queue_status"), table_name="ai_approval_queue")
    op.drop_index(op.f("ix_ai_approval_queue_lead_id"), table_name="ai_approval_queue")
    op.drop_index(op.f("ix_ai_approval_queue_agent_name"), table_name="ai_approval_queue")
    op.drop_table("ai_approval_queue")

    # Drop customer_consents
    op.drop_index(op.f("ix_customer_consents_mobile"), table_name="customer_consents")
    op.drop_table("customer_consents")

    # Drop ai_agent_configs
    op.drop_index(op.f("ix_ai_agent_configs_agent_name"), table_name="ai_agent_configs")
    op.drop_table("ai_agent_configs")
