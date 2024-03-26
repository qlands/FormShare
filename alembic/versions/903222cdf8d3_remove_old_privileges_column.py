"""Remove old privileges column

Revision ID: 903222cdf8d3
Revises: edcb3fdbfc3d
Create Date: 2022-05-21 11:54:35.060211

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "903222cdf8d3"
down_revision = "edcb3fdbfc3d"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("formgrpaccess", "group_privileges")
    op.drop_column("formaccess", "coll_privileges")


def downgrade():
    op.add_column(
        "formgrpaccess",
        sa.Column(
            "group_privileges",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )

    op.add_column(
        "formaccess",
        sa.Column(
            "coll_privileges",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )

    conn = op.get_bind()

    # join the assistant access
    sql = "UPDATE formaccess SET coll_privileges = 1 WHERE coll_can_submit = 1 AND coll_can_clean = 0"
    conn.execute(sql)

    sql = "UPDATE formaccess SET coll_privileges = 2 WHERE coll_can_submit = 0 AND coll_can_clean = 1"
    conn.execute(sql)

    sql = "UPDATE formaccess SET coll_privileges = 3 WHERE coll_can_submit = 1 AND coll_can_clean = 1"
    conn.execute(sql)

    # join the assistant group access

    sql = "UPDATE formgrpaccess SET group_privileges = 1 WHERE group_can_submit = 1 AND group_can_clean = 0"
    conn.execute(sql)

    sql = "UPDATE formgrpaccess SET group_privileges = 2 WHERE group_can_submit = 0 AND group_can_clean = 1"
    conn.execute(sql)

    sql = "UPDATE formgrpaccess SET group_privileges = 3 WHERE group_can_submit = 1 AND group_can_clean = 1"
    conn.execute(sql)
