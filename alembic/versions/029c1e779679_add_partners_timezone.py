"""Add partners timezone

Revision ID: 029c1e779679
Revises: c397ca02529d
Create Date: 2021-12-29 20:54:45.979560

"""

import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "029c1e779679"
down_revision = "c397ca02529d"
branch_labels = None
depends_on = None


def upgrade():
    timezone = datetime.datetime.utcnow().astimezone().tzname()
    conn = op.get_bind()
    sql = "SELECT timezone.timezone_code FROM timezone WHERE timezone.timezone_code = '{}'".format(
        timezone
    )
    res = conn.execute(sql).fetchone()
    if res is None:
        timezone = "UTC"
    op.add_column(
        "partner",
        sa.Column(
            "partner_timezone",
            sa.Unicode(length=64),
            server_default=sa.text("'{}'".format(timezone)),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        op.f("fk_partner_partner_timezone_timezone"),
        "partner",
        "timezone",
        ["partner_timezone"],
        ["timezone_code"],
        ondelete="RESTRICT",
    )


def downgrade():
    op.drop_column("partner", "partner_timezone")
