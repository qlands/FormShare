"""New dictionary fields

Revision ID: d1ef48099a64
Revises: 5bd66e0534e0
Create Date: 2023-06-04 10:19:27.837105

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "d1ef48099a64"
down_revision = "5bd66e0534e0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dictfield",
        sa.Column(
            "field_encrypted",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    op.add_column(
        "dictfield", sa.Column("field_ontology", sa.Unicode(length=120), nullable=True)
    )
    op.add_column(
        "dictfield",
        sa.Column(
            "extras", mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
    )
    op.add_column(
        "dicttable",
        sa.Column(
            "extras", mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
    )


def downgrade():
    op.drop_column("dicttable", "extras")
    op.drop_column("dictfield", "extras")
    op.drop_column("dictfield", "field_ontology")
    op.drop_column("dictfield", "field_encrypted")
