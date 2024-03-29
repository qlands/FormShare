"""Add geopoint to form

Revision ID: e3f8a1c67b18
Revises: d541781210ed
Create Date: 2018-11-29 11:41:57.045857

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e3f8a1c67b18"
down_revision = "d541781210ed"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "odkform", sa.Column("form_geopoint", sa.UnicodeText(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("odkform", "form_geopoint")
    # ### end Alembic commands ###
