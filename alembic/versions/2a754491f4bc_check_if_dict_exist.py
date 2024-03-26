"""Check if dict exist

Revision ID: 2a754491f4bc
Revises: a376b6bc01e1
Create Date: 2021-03-20 12:38:54.808322

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2a754491f4bc"
down_revision = "a376b6bc01e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "odkform",
        sa.Column(
            "form_hasdictionary",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("odkform", "form_hasdictionary")
