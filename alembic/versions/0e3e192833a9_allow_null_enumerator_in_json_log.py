"""Allow null enumerator in json log

Revision ID: 0e3e192833a9
Revises: 37043558e122
Create Date: 2022-05-25 06:50:47.905669

"""
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "0e3e192833a9"
down_revision = "37043558e122"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "jsonlog",
        "enum_project",
        existing_type=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=64),
        nullable=True,
    )
    op.alter_column(
        "jsonlog",
        "coll_id",
        existing_type=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=120),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "jsonlog",
        "coll_id",
        existing_type=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=120),
        nullable=False,
    )
    op.alter_column(
        "jsonlog",
        "enum_project",
        existing_type=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=64),
        nullable=False,
    )
