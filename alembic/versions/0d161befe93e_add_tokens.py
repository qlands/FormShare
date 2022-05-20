"""Add tokens

Revision ID: 0d161befe93e
Revises: a5b33c5e0166
Create Date: 2022-05-20 12:39:27.550723

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0d161befe93e"
down_revision = "a5b33c5e0166"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "fsuser",
        sa.Column("user_password_reset_key", sa.Unicode(length=64), nullable=True),
    )
    op.add_column(
        "fsuser",
        sa.Column("user_password_reset_token", sa.Unicode(length=64), nullable=True),
    )
    op.add_column(
        "fsuser",
        sa.Column("user_password_reset_expires_on", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("fsuser", "user_password_reset_expires_on")
    op.drop_column("fsuser", "user_password_reset_token")
    op.drop_column("fsuser", "user_password_reset_key")
