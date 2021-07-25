"""New fields to case management

Revision ID: 088eb7b9320c
Revises: 221d9f82a10d
Create Date: 2021-03-10 09:29:41.140453

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "088eb7b9320c"
down_revision = "221d9f82a10d"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "odkform",
        sa.Column(
            "form_case", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )
    op.add_column(
        "odkform", sa.Column("form_caselabel", sa.Unicode(length=120), nullable=True)
    )
    op.add_column(
        "odkform", sa.Column("form_caseselector", sa.Unicode(length=120), nullable=True)
    )
    op.add_column(
        "odkform",
        sa.Column("form_caseselectorfilename", sa.Unicode(length=120), nullable=True),
    )
    op.add_column(
        "odkform",
        sa.Column(
            "form_casetype", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )
    op.add_column(
        "project",
        sa.Column(
            "project_case", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("project", "project_case")
    op.drop_column("odkform", "form_casetype")
    op.drop_column("odkform", "form_caseselectorfilename")
    op.drop_column("odkform", "form_caseselector")
    op.drop_column("odkform", "form_caselabel")
    op.drop_column("odkform", "form_case")
    # ### end Alembic commands ###
