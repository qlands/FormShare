"""Add Time Zone to project table

Revision ID: f8c1d300451e
Revises: 72e2baa007bd
Create Date: 2021-12-18 11:57:40.858512

"""
from alembic import op
import sqlalchemy as sa
import datetime


# revision identifiers, used by Alembic.
revision = "f8c1d300451e"
down_revision = "72e2baa007bd"
branch_labels = None
depends_on = None


def upgrade():
    timezone = datetime.datetime.utcnow().astimezone().tzname()
    sql = "SELECT timezone.timezone_code FROM timezone WHERE timezone.timezone_code = '{}'".format(
        timezone
    )
    conn = op.get_bind()
    res = conn.execute(sql)
    if res is None:
        timezone = "UTC"
    op.add_column(
        "project",
        sa.Column(
            "project_timezone",
            sa.Unicode(length=64),
            server_default=sa.text("'{}'".format(timezone)),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        op.f("fk_project_project_timezone_timezone"),
        "project",
        "timezone",
        ["project_timezone"],
        ["timezone_code"],
        ondelete="RESTRICT",
    )


def downgrade():
    op.drop_column("project", "project_timezone")
