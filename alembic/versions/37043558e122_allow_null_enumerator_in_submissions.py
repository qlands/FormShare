"""Allow null enumerator in submissions

Revision ID: 37043558e122
Revises: 9c097f543c77
Create Date: 2022-05-24 21:12:24.895112

"""
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "37043558e122"
down_revision = "9c097f543c77"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "submission",
        "enum_project",
        existing_type=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=64),
        nullable=True,
    )
    op.alter_column(
        "submission",
        "coll_id",
        existing_type=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=120),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        "submission",
        "coll_id",
        existing_type=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=120),
        nullable=False,
    )
    op.alter_column(
        "submission",
        "enum_project",
        existing_type=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=64),
        nullable=False,
    )
