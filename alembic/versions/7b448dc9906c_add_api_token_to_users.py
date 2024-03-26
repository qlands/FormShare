"""Add API token to users

Revision ID: 7b448dc9906c
Revises: f1917c3e8546
Create Date: 2022-05-11 07:26:32.497902

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7b448dc9906c"
down_revision = "f1917c3e8546"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "fsuser", sa.Column("user_apitoken", sa.Unicode(length=64), nullable=True)
    )
    op.add_column(
        "fsuser", sa.Column("user_apitoken_expires_on", sa.DateTime(), nullable=True)
    )


def downgrade():
    op.drop_column("fsuser", "user_apitoken_expires_on")
    op.drop_column("fsuser", "user_apitoken")
