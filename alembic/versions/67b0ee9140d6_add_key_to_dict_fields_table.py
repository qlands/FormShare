"""Add key to dict fields table

Revision ID: 67b0ee9140d6
Revises: 01b3430ed67e
Create Date: 2021-03-21 16:37:46.284602

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "67b0ee9140d6"
down_revision = "01b3430ed67e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dictfield",
        sa.Column(
            "field_key", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )


def downgrade():
    op.drop_column("dictfield", "field_key")
