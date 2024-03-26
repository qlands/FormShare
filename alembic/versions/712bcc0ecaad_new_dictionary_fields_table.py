"""New dictionary fields table

Revision ID: 712bcc0ecaad
Revises: 5049a7318233
Create Date: 2021-03-20 08:34:53.793426

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "712bcc0ecaad"
down_revision = "5049a7318233"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dictfield",
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("form_id", sa.Unicode(length=120), nullable=False),
        sa.Column("table_name", sa.Unicode(length=120), nullable=False),
        sa.Column("field_name", sa.Unicode(length=120), nullable=False),
        sa.Column("field_desc", sa.UnicodeText(), nullable=True),
        sa.Column("field_xmlcode", sa.UnicodeText(), nullable=True),
        sa.Column("field_type", sa.Unicode(length=64), nullable=True),
        sa.Column("field_odktype", sa.Unicode(length=64), nullable=True),
        sa.Column("field_rtable", sa.Unicode(length=120), nullable=True),
        sa.Column("field_rfield", sa.Unicode(length=120), nullable=True),
        sa.Column(
            "field_rlookup", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
        sa.Column("field_rname", sa.Unicode(length=64), nullable=True),
        sa.Column(
            "field_selecttype",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
        sa.Column("field_externalfilename", sa.UnicodeText(), nullable=True),
        sa.Column(
            "field_size", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
        sa.Column(
            "field_decsize", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "form_id", "table_name"],
            ["dicttable.project_id", "dicttable.form_id", "dicttable.table_name"],
            name=op.f("fk_dictfield_project_id_dicttable"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id",
            "form_id",
            "table_name",
            "field_name",
            name=op.f("pk_dictfield"),
        ),
        mysql_charset="utf8",
        mysql_engine="InnoDB",
    )


def downgrade():
    op.drop_table("dictfield")
