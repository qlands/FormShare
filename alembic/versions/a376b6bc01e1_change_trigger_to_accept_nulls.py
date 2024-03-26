"""Change trigger to accept nulls

Revision ID: a376b6bc01e1
Revises: 2e584da970a8
Create Date: 2021-03-20 12:09:03.716572

"""

from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "a376b6bc01e1"
down_revision = "2e584da970a8"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "dicttable",
        "table_inserttrigger",
        existing_type=mysql.VARCHAR(length=64),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "dicttable",
        "table_inserttrigger",
        existing_type=mysql.VARCHAR(length=64),
        nullable=False,
    )
