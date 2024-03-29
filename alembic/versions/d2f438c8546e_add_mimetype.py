"""Add mimetype

Revision ID: d2f438c8546e
Revises: cf06416c1d0e
Create Date: 2018-11-25 11:41:57.078185

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d2f438c8546e"
down_revision = "cf06416c1d0e"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "mediafile", sa.Column("file_mimetype", sa.Unicode(length=64), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("mediafile", "file_mimetype")
    # ### end Alembic commands ###
