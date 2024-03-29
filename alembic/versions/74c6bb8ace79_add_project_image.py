"""Add project image

Revision ID: 74c6bb8ace79
Revises: cb71f27114e5
Create Date: 2018-11-08 11:35:08.498906

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "74c6bb8ace79"
down_revision = "cb71f27114e5"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "project", sa.Column("project_image", sa.UnicodeText(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("project", "project_image")
    # ### end Alembic commands ###
