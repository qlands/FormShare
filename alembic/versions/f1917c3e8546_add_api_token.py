"""Add API token

Revision ID: f1917c3e8546
Revises: ebe16efbc30f
Create Date: 2022-05-11 06:54:50.897307

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1917c3e8546"
down_revision = "ebe16efbc30f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "collaborator", sa.Column("coll_apitoken", sa.Unicode(length=64), nullable=True)
    )
    op.add_column(
        "collaborator",
        sa.Column("coll_apitoken_expires_on", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("collaborator", "coll_apitoken_expires_on")
    op.drop_column("collaborator", "coll_apitoken")
