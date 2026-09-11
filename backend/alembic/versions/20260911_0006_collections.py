"""create collections table

Revision ID: 20260911_0006_collections
Revises: 20260911_0005_invite_declines
Create Date: 2026-09-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260911_0006_collections"
down_revision = "20260911_0005_invite_declines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collections",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_by", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_collections_workspace_id", "collections", ["workspace_id"], unique=False)
    op.create_index("ix_collections_created_by", "collections", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_collections_created_by", table_name="collections")
    op.drop_index("ix_collections_workspace_id", table_name="collections")
    op.drop_table("collections")