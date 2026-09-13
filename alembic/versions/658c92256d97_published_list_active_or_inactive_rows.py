"""Published list active or inactive rows

Adds list_active to publishedlist: whether a list serves active (1, the
default) or inactive (0) rows. All data tables now carry _active, so a list
generated from any of them can serve one or the other -- a follow-up over
active cases, a separate list over inactive ones.

Revision ID: 658c92256d97
Revises: 9694cae805c9
Create Date: 2026-09-13

"""

from alembic import op
import sqlalchemy as sa

revision = "658c92256d97"
down_revision = "9694cae805c9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "publishedlist",
        sa.Column(
            "list_active",
            sa.INTEGER(),
            server_default=sa.text("'1'"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("publishedlist", "list_active")
