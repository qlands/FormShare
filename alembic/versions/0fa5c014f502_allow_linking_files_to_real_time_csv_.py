"""Allow linking files to real-time CSV case file

Revision ID: 0fa5c014f502
Revises: e29a5b751eb5
Create Date: 2024-04-22 16:09:47.210109

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0fa5c014f502"
down_revision = "e29a5b751eb5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "mediafile",
        sa.Column(
            "file_realtimecsv",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    op.add_column("mediafile", sa.Column("file_lastgen", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("mediafile", "file_lastgen")
    op.drop_column("mediafile", "file_realtimecsv")
