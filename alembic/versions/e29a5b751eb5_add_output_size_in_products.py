"""Add output size in products

Revision ID: e29a5b751eb5
Revises: 1903afedb92d
Create Date: 2024-04-05 13:16:07.249590

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
import os

# revision identifiers, used by Alembic.
revision = "e29a5b751eb5"
down_revision = "1903afedb92d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "product",
        sa.Column(
            "output_size",
            mysql.BIGINT(unsigned=True),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    conn = op.get_bind()
    sql = "SELECT celery_taskid, output_file FROM product WHERE output_file is not null"
    products = conn.execute(sql).fetchall()
    for a_product in products:
        if os.path.exists(a_product[1]):
            file_stats = os.stat(a_product[1])
            file_size = file_stats.st_size
            sql = (
                "UPDATE product SET output_size = {} WHERE celery_taskid = '{}'".format(
                    file_size, a_product[0]
                )
            )
            conn.execute(sql)


def downgrade():
    op.drop_column("product", "output_size")
