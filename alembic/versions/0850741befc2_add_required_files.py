"""Add required files

Revision ID: 0850741befc2
Revises: 25bbfe2293d0
Create Date: 2019-02-24 12:21:22.195810

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0850741befc2"
down_revision = "25bbfe2293d0"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "odkform", sa.Column("form_reqfiles", sa.UnicodeText(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("odkform", "form_reqfiles")
    # ### end Alembic commands ###
