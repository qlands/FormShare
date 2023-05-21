"""Store extra columns

Revision ID: 5bd66e0534e0
Revises: e2d6d5aa3700
Create Date: 2023-05-20 11:31:44.540336

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "5bd66e0534e0"
down_revision = "e2d6d5aa3700"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "odkform",
        sa.Column(
            "form_surveycolumns",
            mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"),
            nullable=True,
        ),
    )
    op.add_column(
        "odkform",
        sa.Column(
            "form_choicescolumns",
            mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"),
            nullable=True,
        ),
    )
    op.add_column(
        "odkform",
        sa.Column(
            "form_invalidcolumns",
            mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("odkform", "form_invalidcolumns")
    op.drop_column("odkform", "form_choicescolumns")
    op.drop_column("odkform", "form_surveycolumns")
