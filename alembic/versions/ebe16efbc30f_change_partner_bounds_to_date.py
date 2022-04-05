"""Change partner bounds to date

Revision ID: ebe16efbc30f
Revises: e061a90d9071
Create Date: 2022-04-05 09:10:11.821122

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "ebe16efbc30f"
down_revision = "e061a90d9071"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "partnerform",
        "access_from",
        existing_type=mysql.DATETIME(),
        type_=sa.Date(),
        existing_nullable=True,
    )
    op.alter_column(
        "partnerform",
        "access_to",
        existing_type=mysql.DATETIME(),
        type_=sa.Date(),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "partnerform",
        "access_to",
        existing_type=sa.Date(),
        type_=mysql.DATETIME(),
        existing_nullable=True,
    )
    op.alter_column(
        "partnerform",
        "access_from",
        existing_type=sa.Date(),
        type_=mysql.DATETIME(),
        existing_nullable=True,
    )
