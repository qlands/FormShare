"""Allow public form list

Revision ID: 6f42a78a93cc
Revises: 0d161befe93e
Create Date: 2022-05-21 08:23:20.055988

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6f42a78a93cc"
down_revision = "0d161befe93e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "project",
        sa.Column(
            "project_formlist_auth",
            sa.INTEGER(),
            server_default=sa.text("'1'"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("project", "project_formlist_auth")
