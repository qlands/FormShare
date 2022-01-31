"""Add Time Zone to user table

Revision ID: ea3ded7f2b62
Revises: f8c1d300451e
Create Date: 2021-12-18 15:54:04.554001

"""
from alembic import op
import sqlalchemy as sa
import datetime

# revision identifiers, used by Alembic.
revision = "ea3ded7f2b62"
down_revision = "f8c1d300451e"
branch_labels = None
depends_on = None


def upgrade():
    timezone = datetime.datetime.utcnow().astimezone().tzname()
    sql = "SELECT timezone.timezone_code FROM timezone WHERE timezone.timezone_code = '{}'".format(
        timezone
    )
    res = conn.execute(sql)
    if res is None:
        timezone = "UTC"
    op.add_column(
        "fsuser",
        sa.Column(
            "user_timezone",
            sa.Unicode(length=64),
            server_default=sa.text("'{}'".format(timezone)),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        op.f("fk_fsuser_user_timezone_timezone"),
        "fsuser",
        "timezone",
        ["user_timezone"],
        ["timezone_code"],
        ondelete="RESTRICT",
    )


def downgrade():
    op.drop_column("fsuser", "user_timezone")
