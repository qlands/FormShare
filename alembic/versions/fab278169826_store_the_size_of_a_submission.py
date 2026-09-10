"""Store the size of a submission

Revision ID: fab278169826
Revises: c60e2c26f353
Create Date: 2026-09-07 13:42:39.594199

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "fab278169826"
down_revision = "c60e2c26f353"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "submission",
        sa.Column(
            "submission_size",
            mysql.BIGINT(unsigned=True),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("submission", "submission_size")
