"""Add field index

Revision ID: cc445e8657bf
Revises: 82aca4b87729
Create Date: 2021-03-21 09:05:21.689678

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "cc445e8657bf"
down_revision = "82aca4b87729"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dictfield",
        sa.Column("field_index", sa.BigInteger, autoincrement=True, nullable=True),
    )
    op.create_index(
        op.f("ix_dictfield_field_index"), "dictfield", ["field_index"], unique=True
    )
    conn = op.get_bind()
    conn.execute(
        "ALTER TABLE dictfield MODIFY COLUMN field_index BIGINT AUTO_INCREMENT"
    )


def downgrade():
    op.drop_column("dictfield", "field_index")
