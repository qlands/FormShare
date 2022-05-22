"""Separate assistant privileges

Revision ID: edcb3fdbfc3d
Revises: 6f42a78a93cc
Create Date: 2022-05-21 11:31:06.801347

"""
from alembic import op
import sqlalchemy as sa
from formshare.models.formshare import Formacces, Formgrpacces
from sqlalchemy.orm.session import Session

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
    session = Session(bind=op.get_bind())

    # Separate the current assistant access
    session.query(Formacces).filter(Formacces.coll_privileges == 1).update(
        {"coll_can_submit": 1}
    )
    session.query(Formacces).filter(Formacces.coll_privileges == 2).update(
        {"coll_can_clean": 1}
    )
    session.query(Formacces).filter(Formacces.coll_privileges == 3).update(
        {"coll_can_submit": 1, "coll_can_clean": 1}
    )

    # Separate curren group access
    session.query(Formgrpacces).filter(Formgrpacces.group_privileges == 1).update(
        {"group_can_submit": 1}
    )
    session.query(Formgrpacces).filter(Formgrpacces.group_privileges == 2).update(
        {"group_can_clean": 1}
    )
    session.query(Formgrpacces).filter(Formgrpacces.group_privileges == 3).update(
        {"group_can_submit": 1, "group_can_clean": 1}
    )
    session.commit()


def downgrade():
    op.drop_column("formgrpaccess", "group_is_supervisor")
    op.drop_column("formgrpaccess", "group_can_clean")
    op.drop_column("formgrpaccess", "group_can_submit")
    op.drop_column("formaccess", "coll_is_supervisor")
    op.drop_column("formaccess", "coll_can_clean")
    op.drop_column("formaccess", "coll_can_submit")
