"""Remove unnecessary field

Revision ID: 9c097f543c77
Revises: 903222cdf8d3
Create Date: 2022-05-22 07:23:18.373730

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9c097f543c77"
down_revision = "903222cdf8d3"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("collingroup", "coll_privileges")


def downgrade():
    op.add_column(
        "collingroup",
        sa.Column(
            "coll_privileges",
            sa.INTEGER(),
            server_default=sa.text("'1'"),
            nullable=True,
        ),
    )
