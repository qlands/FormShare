"""Published list keyed by a column

Adds list_key_column to publishedlist. NULL (the default) is a row list: name
is the source row's rowuuid, one row per source row, linkable as a case.
Set, it is a value list: SELECT DISTINCT over that column, name and label
are values, one row per distinct value -- a list of districts pulled from a
table of schools. A value list cannot be a case link: its key is neither
unique nor a rowuuid, so there is nothing to foreign-key to.

Revision ID: 1810d0dba954
Revises: 658c92256d97
Create Date: 2026-09-16

"""

from alembic import op
import sqlalchemy as sa

revision = "1810d0dba954"
down_revision = "658c92256d97"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "publishedlist",
        sa.Column("list_key_column", sa.Unicode(length=120), nullable=True),
    )


def downgrade():
    op.drop_column("publishedlist", "list_key_column")
