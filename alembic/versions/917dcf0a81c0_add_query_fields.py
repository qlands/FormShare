"""Add query fields

Revision ID: 917dcf0a81c0
Revises: 0e3e192833a9
Create Date: 2022-10-17 14:32:16.845673

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "917dcf0a81c0"
down_revision = "0e3e192833a9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "collaborator",
        sa.Column("coll_query_user", sa.Unicode(length=64), nullable=True),
    )
    op.add_column(
        "collaborator",
        sa.Column("coll_query_password", sa.Unicode(length=256), nullable=True),
    )
    op.add_column(
        "formaccess",
        sa.Column(
            "coll_can_query", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )
    op.add_column(
        "fsuser", sa.Column("user_query_user", sa.Unicode(length=64), nullable=True)
    )
    op.add_column(
        "fsuser",
        sa.Column("user_query_password", sa.Unicode(length=256), nullable=True),
    )
    op.add_column(
        "partner", sa.Column("partner_query_user", sa.Unicode(length=64), nullable=True)
    )
    op.add_column(
        "partner",
        sa.Column("partner_query_password", sa.Unicode(length=256), nullable=True),
    )
    op.add_column(
        "partnerform",
        sa.Column(
            "query_access", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )
    op.add_column(
        "partnerproject",
        sa.Column(
            "query_access", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )


def downgrade():
    op.drop_column("partnerproject", "query_access")
    op.drop_column("partnerform", "query_access")
    op.drop_column("partner", "partner_query_password")
    op.drop_column("partner", "partner_query_user")
    op.drop_column("fsuser", "user_query_password")
    op.drop_column("fsuser", "user_query_user")
    op.drop_column("formaccess", "coll_can_query")
    op.drop_column("collaborator", "coll_query_password")
    op.drop_column("collaborator", "coll_query_user")
