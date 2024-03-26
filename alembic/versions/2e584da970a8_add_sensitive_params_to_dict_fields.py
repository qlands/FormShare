"""Add sensitive params to dict fields

Revision ID: 2e584da970a8
Revises: 712bcc0ecaad
Create Date: 2021-03-20 09:06:45.829574

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2e584da970a8"
down_revision = "712bcc0ecaad"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dictfield", sa.Column("field_protection", sa.Unicode(length=64), nullable=True)
    )
    op.add_column(
        "dictfield",
        sa.Column(
            "field_sensitive",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("dictfield", "field_sensitive")
    op.drop_column("dictfield", "field_protection")
