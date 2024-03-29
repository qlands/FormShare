"""Add group access

Revision ID: ebd3f0076513
Revises: 415a14a81315
Create Date: 2018-11-21 07:25:18.774155

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "ebd3f0076513"
down_revision = "415a14a81315"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "formgrpaccess", sa.Column("group_privileges", sa.INTEGER(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("formgrpaccess", "group_privileges")
    # ### end Alembic commands ###
