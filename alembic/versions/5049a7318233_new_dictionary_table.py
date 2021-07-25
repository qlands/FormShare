"""New dictionary table

Revision ID: 5049a7318233
Revises: 088eb7b9320c
Create Date: 2021-03-20 08:12:31.021821

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5049a7318233"
down_revision = "088eb7b9320c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dicttable",
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("form_id", sa.Unicode(length=120), nullable=False),
        sa.Column("table_name", sa.Unicode(length=120), nullable=False),
        sa.Column("table_desc", sa.UnicodeText(), nullable=False),
        sa.Column(
            "table_lkp", sa.INTEGER(), server_default=sa.text("'0'"), nullable=False
        ),
        sa.Column("table_inserttrigger", sa.Unicode(length=64), nullable=False),
        sa.Column("table_xmlcode", sa.UnicodeText(), nullable=True),
        sa.Column("parent_project", sa.Unicode(length=64), nullable=True),
        sa.Column("parent_form", sa.Unicode(length=120), nullable=True),
        sa.Column("parent_table", sa.Unicode(length=120), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_project", "parent_form", "parent_table"],
            ["dicttable.project_id", "dicttable.form_id", "dicttable.table_name"],
            name=op.f("fk_dicttable_parent_project_dicttable"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            name=op.f("fk_dicttable_project_id_odkform"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "form_id", "table_name", name=op.f("pk_dicttable")
        ),
        mysql_charset="utf8",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "fk_dicttable_dicttable_idx",
        "dicttable",
        ["parent_project", "parent_form", "parent_table"],
        unique=False,
    )


def downgrade():
    op.drop_table("dicttable")
