"""Add formshare_unique

Revision ID: 75ded009ddaa
Revises: 04268f3259f2
Create Date: 2023-07-27 12:56:51.314847

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "75ded009ddaa"
down_revision = "04268f3259f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dictfield",
        sa.Column(
            "field_unique", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )


def downgrade():
    op.drop_column("dictfield", "field_unique")
