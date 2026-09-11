"""add invite decline timestamps

Revision ID: 20260911_0005_invite_declines
Revises: 20260911_0004_workspace_invites
"""

from alembic import op
import sqlalchemy as sa


revision = "20260911_0005_invite_declines"
down_revision = "20260911_0004_workspace_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspace_invites", sa.Column("declined_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("workspace_invites", "declined_at")