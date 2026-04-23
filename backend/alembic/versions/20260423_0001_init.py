"""init schema

Revision ID: 20260423_0001
Revises:
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260423_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("balance", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("engine_id", sa.Integer(), nullable=False),
        sa.Column("version_type", sa.String(length=50), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("original_path", sa.Text(), nullable=False),
        sa.Column("req_doc_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_expedited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("output_path", sa.Text(), nullable=True),
        sa.Column("log_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "modify_instructions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("target_file", sa.Text(), nullable=False),
        sa.Column("operation", sa.String(length=20), nullable=False),
        sa.Column("old_content", sa.Text(), nullable=True),
        sa.Column("new_content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("modify_instructions")
    op.drop_table("tasks")
    op.drop_table("users")
