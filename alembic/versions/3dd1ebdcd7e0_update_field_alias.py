"""Update field alias

Revision ID: 3dd1ebdcd7e0
Revises: 61535009c882
Create Date: 2021-03-27 10:28:33.179167

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "3dd1ebdcd7e0"
down_revision = "61535009c882"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "caselookup",
        "field_as",
        existing_type=mysql.VARCHAR(length=45),
        type_=sa.Unicode(length=120),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "caselookup",
        "field_as",
        existing_type=sa.Unicode(length=120),
        type_=mysql.VARCHAR(length=45),
        existing_nullable=True,
    )
