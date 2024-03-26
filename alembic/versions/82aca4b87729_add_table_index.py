"""Add table index

Revision ID: 82aca4b87729
Revises: 2a754491f4bc
Create Date: 2021-03-21 08:49:48.758600

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "82aca4b87729"
down_revision = "2a754491f4bc"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dicttable",
        sa.Column("table_index", sa.BigInteger, autoincrement=True, nullable=True),
    )
    op.create_index(
        op.f("ix_dicttable_table_index"), "dicttable", ["table_index"], unique=True
    )
    conn = op.get_bind()
    conn.execute(
        "ALTER TABLE dicttable MODIFY COLUMN table_index BIGINT AUTO_INCREMENT"
    )


def downgrade():
    op.drop_column("dicttable", "table_index")
