"""Add md5 and last download

Revision ID: cf06416c1d0e
Revises: 9498f8e802f6
Create Date: 2018-11-25 10:15:21.194133

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "cf06416c1d0e"
down_revision = "9498f8e802f6"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("mediafile", sa.Column("file_lstdwnld", sa.DateTime(), nullable=True))
    op.add_column(
        "mediafile", sa.Column("file_md5", sa.Unicode(length=64), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("mediafile", "file_md5")
    op.drop_column("mediafile", "file_lstdwnld")
    # ### end Alembic commands ###