"""Add product description

Revision ID: f3467525faa2
Revises: e3cbc92b0a17
Create Date: 2021-12-04 14:07:01.031865

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3467525faa2"
down_revision = "e3cbc92b0a17"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "product", sa.Column("product_desc", sa.Unicode(length=120), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("product", "product_desc")
    # ### end Alembic commands ###
