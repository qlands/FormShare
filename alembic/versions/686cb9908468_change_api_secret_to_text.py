"""Change API secret to text

Revision ID: 686cb9908468
Revises: 917dcf0a81c0
Create Date: 2022-11-11 18:43:09.187955

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "686cb9908468"
down_revision = "917dcf0a81c0"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "collaborator",
        "coll_apisecret",
        existing_type=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=64),
        type_=mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"),
        existing_nullable=True,
    )
    op.alter_column(
        "fsuser",
        "user_apisecret",
        existing_type=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=64),
        type_=mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "fsuser",
        "user_apisecret",
        existing_type=mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"),
        type_=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=64),
        existing_nullable=True,
    )
    op.alter_column(
        "collaborator",
        "coll_apisecret",
        existing_type=mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"),
        type_=mysql.VARCHAR(collation="utf8mb4_unicode_ci", length=64),
        existing_nullable=True,
    )
