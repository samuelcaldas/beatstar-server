"""Create administrator user and revocable session tables.

Revision ID: 0001_admin_auth
Revises:
"""

import sqlalchemy as sa
from alembic import op
from fastapi_users_db_sqlalchemy.generics import GUID, TIMESTAMPAware

revision = "0001_admin_auth"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Creates the administrator and access-token tables used by fastapi-users."""
    op.create_table(
        "user",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)
    op.create_table(
        "accesstoken",
        sa.Column("token", sa.String(length=43), nullable=False),
        sa.Column("created_at", TIMESTAMPAware(timezone=True), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="cascade"),
        sa.PrimaryKeyConstraint("token"),
    )
    op.create_index(op.f("ix_accesstoken_created_at"), "accesstoken", ["created_at"], unique=False)


def downgrade() -> None:
    """Drops the session table before the administrator table it references."""
    op.drop_index(op.f("ix_accesstoken_created_at"), table_name="accesstoken")
    op.drop_table("accesstoken")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
