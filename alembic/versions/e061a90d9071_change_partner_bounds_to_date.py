"""Change partner bounds to date

Revision ID: e061a90d9071
Revises: 029c1e779679
Create Date: 2022-04-03 21:19:27.788492

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "e061a90d9071"
down_revision = "029c1e779679"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "partnerproject",
        "access_from",
        existing_type=mysql.DATETIME(),
        type_=sa.Date(),
        existing_nullable=True,
    )
    op.alter_column(
        "partnerproject",
        "access_to",
        existing_type=mysql.DATETIME(),
        type_=sa.Date(),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "partnerproject",
        "access_to",
        existing_type=sa.Date(),
        type_=mysql.DATETIME(),
        existing_nullable=True,
    )
    op.alter_column(
        "partnerproject",
        "access_from",
        existing_type=sa.Date(),
        type_=mysql.DATETIME(),
        existing_nullable=True,
    )
