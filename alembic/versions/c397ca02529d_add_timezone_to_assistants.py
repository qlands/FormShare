"""Add timezone to assistants

Revision ID: c397ca02529d
Revises: ea3ded7f2b62
Create Date: 2021-12-28 09:34:27.579820

"""
from alembic import op
import sqlalchemy as sa
import datetime


# revision identifiers, used by Alembic.
revision = "c397ca02529d"
down_revision = "ea3ded7f2b62"
branch_labels = None
depends_on = None


def upgrade():
    timezone = datetime.datetime.utcnow().astimezone().tzname()
    conn = op.get_bind()
    sql = "SELECT timezone.timezone_code FROM timezone WHERE timezone.timezone_code = '{}'".format(
        timezone
    )
    res = conn.execute(sql)
    if res is None:
        timezone = "UTC"
    op.add_column(
        "collaborator",
        sa.Column(
            "coll_timezone",
            sa.Unicode(length=64),
            server_default=sa.text("'{}'".format(timezone)),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        op.f("fk_collaborator_coll_timezone_timezone"),
        "collaborator",
        "timezone",
        ["coll_timezone"],
        ["timezone_code"],
        ondelete="RESTRICT",
    )


def downgrade():
    op.drop_column("collaborator", "coll_timezone")
