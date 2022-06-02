"""Separate assistant privileges

Revision ID: edcb3fdbfc3d
Revises: 6f42a78a93cc
Create Date: 2022-05-21 11:31:06.801347

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "edcb3fdbfc3d"
down_revision = "6f42a78a93cc"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "formaccess",
        sa.Column(
            "coll_can_submit",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    op.add_column(
        "formaccess",
        sa.Column(
            "coll_can_clean", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )
    op.add_column(
        "formaccess",
        sa.Column(
            "coll_is_supervisor",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    op.add_column(
        "formgrpaccess",
        sa.Column(
            "group_can_submit",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    op.add_column(
        "formgrpaccess",
        sa.Column(
            "group_can_clean",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    op.add_column(
        "formgrpaccess",
        sa.Column(
            "group_is_supervisor",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )

    conn = op.get_bind()

    # Separate the current assistant access
    sql = "UPDATE formaccess SET coll_can_submit = 1, coll_can_clean = 0 WHERE coll_privileges = 1"
    conn.execute(sql)

    sql = "UPDATE formaccess SET coll_can_submit = 0, coll_can_clean = 1 WHERE coll_privileges = 2"
    conn.execute(sql)

    sql = "UPDATE formaccess SET coll_can_submit = 1, coll_can_clean = 1 WHERE coll_privileges = 3"
    conn.execute(sql)

    # Separate curren group access
    sql = "UPDATE formgrpaccess SET group_can_submit = 1, group_can_clean = 0 WHERE group_privileges = 1"
    conn.execute(sql)

    sql = "UPDATE formgrpaccess SET group_can_submit = 0, group_can_clean = 1 WHERE group_privileges = 2"
    conn.execute(sql)

    sql = "UPDATE formgrpaccess SET group_can_submit = 1, group_can_clean = 1 WHERE group_privileges = 3"
    conn.execute(sql)


def downgrade():
    op.drop_column("formgrpaccess", "group_is_supervisor")
    op.drop_column("formgrpaccess", "group_can_clean")
    op.drop_column("formgrpaccess", "group_can_submit")
    op.drop_column("formaccess", "coll_is_supervisor")
    op.drop_column("formaccess", "coll_can_clean")
    op.drop_column("formaccess", "coll_can_submit")
