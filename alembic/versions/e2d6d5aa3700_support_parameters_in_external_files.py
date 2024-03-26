"""Support parameters in external files

Revision ID: e2d6d5aa3700
Revises: e1fef7492afb
Create Date: 2022-11-30 18:07:33.496699

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e2d6d5aa3700"
down_revision = "e1fef7492afb"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dictfield",
        sa.Column("field_codecolumn", sa.Unicode(length=120), nullable=True),
    )
    op.add_column(
        "dictfield",
        sa.Column("field_desccolumn", sa.Unicode(length=120), nullable=True),
    )


def downgrade():
    op.drop_column("dictfield", "field_desccolumn")
    op.drop_column("dictfield", "field_codecolumn")
