"""create initial tables

Revision ID: 5ff95bda6ec8
Revises:
Create Date: 2026-09-21 17:48:14.007983
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5ff95bda6ec8"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database tables."""

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now()
        ),
    )

    op.create_table(
        "chat_rooms",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now()
        ),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "room_id",
            sa.Integer(),
            sa.ForeignKey("chat_rooms.id"),
            nullable=False
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False
        ),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now()
        ),
    )

    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "room_id",
            sa.Integer(),
            sa.ForeignKey("chat_rooms.id"),
            nullable=False
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    """Remove database tables."""

    op.drop_table("uploaded_files")
    op.drop_table("chat_messages")
    op.drop_table("chat_rooms")
    op.drop_table("users")