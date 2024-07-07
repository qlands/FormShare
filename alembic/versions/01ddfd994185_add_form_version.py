"""Add form version

Revision ID: 01ddfd994185
Revises: 0fa5c014f502
Create Date: 2024-07-07 09:12:59.512741

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "01ddfd994185"
down_revision = "0fa5c014f502"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "odkform",
        sa.Column(
            "form_version",
            mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("odkform", "form_version")
