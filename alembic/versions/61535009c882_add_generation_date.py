"""Add generation date

Revision ID: 61535009c882
Revises: 67b0ee9140d6
Create Date: 2021-03-27 10:26:37.263965

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "61535009c882"
down_revision = "67b0ee9140d6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "odkform", sa.Column("form_caseselectorlastgen", sa.DateTime(), nullable=True)
    )


def downgrade():
    op.drop_column("odkform", "form_caseselectorlastgen")
