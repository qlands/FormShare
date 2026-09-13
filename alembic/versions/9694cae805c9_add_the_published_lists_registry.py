"""Add the published lists registry

The three tables of stage 1 of native case management
(docs/formshare_case_management/formshare.md section 2): the registry of
real-time files a project publishes, the columns each serves, and the record
of which forms consume which list.

Revision ID: 9694cae805c9
Revises: fab278169826
Create Date: 2026-09-12

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "9694cae805c9"
down_revision = "fab278169826"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "publishedlist",
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("list_id", sa.Unicode(length=120), nullable=False),
        sa.Column("list_filename", sa.Unicode(length=120), nullable=False),
        sa.Column(
            "list_format",
            sa.Unicode(length=12),
            server_default=sa.text("'csv'"),
            nullable=False,
        ),
        sa.Column("source_project", sa.Unicode(length=64), nullable=False),
        sa.Column("source_form", sa.Unicode(length=120), nullable=False),
        sa.Column("source_table", sa.Unicode(length=120), nullable=False),
        sa.Column("label_column", sa.Unicode(length=120), nullable=False),
        sa.Column(
            "filter_sql",
            mysql.MEDIUMTEXT(),
            nullable=True,
        ),
        sa.Column("geometry_column", sa.Unicode(length=120), nullable=True),
        sa.Column(
            "list_filter_mode",
            sa.Unicode(length=20),
            server_default=sa.text("'all'"),
            nullable=True,
        ),
        sa.Column("list_lastgen", sa.DateTime(), nullable=True),
        sa.Column(
            "list_seq", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
        sa.Column("list_createdate", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            ondelete="CASCADE",
            name=op.f("fk_publishedlist_project_id_project"),
        ),
        # The source form is protected while a list drinks from it: RESTRICT
        # is the backstop behind the application-level delete guard.
        sa.ForeignKeyConstraint(
            ["source_project", "source_form"],
            ["odkform.project_id", "odkform.form_id"],
            name=op.f("fk_publishedlist_source_odkform"),
        ),
        sa.PrimaryKeyConstraint("project_id", "list_id", name=op.f("pk_publishedlist")),
        sa.UniqueConstraint(
            "project_id", "list_filename", name=op.f("uq_publishedlist_filename")
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "publishedlistcolumn",
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("list_id", sa.Unicode(length=120), nullable=False),
        sa.Column("column_name", sa.Unicode(length=120), nullable=False),
        sa.Column(
            "column_source",
            sa.Unicode(length=20),
            server_default=sa.text("'table'"),
            nullable=False,
        ),
        sa.Column("column_as", sa.Unicode(length=120), nullable=True),
        sa.Column(
            "column_order", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "list_id"],
            ["publishedlist.project_id", "publishedlist.list_id"],
            ondelete="CASCADE",
            name=op.f("fk_publishedlistcolumn_publishedlist"),
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "list_id", "column_name", name=op.f("pk_publishedlistcolumn")
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "listconsumer",
        sa.Column("list_project", sa.Unicode(length=64), nullable=False),
        sa.Column("list_id", sa.Unicode(length=120), nullable=False),
        sa.Column("consumer_project", sa.Unicode(length=64), nullable=False),
        sa.Column("consumer_form", sa.Unicode(length=120), nullable=False),
        sa.Column(
            "consumer_role",
            sa.Unicode(length=20),
            server_default=sa.text("'reads'"),
            nullable=False,
        ),
        sa.Column("selector_field", sa.Unicode(length=120), nullable=True),
        sa.Column(
            "consumer_is_link",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["list_project", "list_id"],
            ["publishedlist.project_id", "publishedlist.list_id"],
            ondelete="CASCADE",
            name=op.f("fk_listconsumer_publishedlist"),
        ),
        sa.ForeignKeyConstraint(
            ["consumer_project", "consumer_form"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
            name=op.f("fk_listconsumer_odkform"),
        ),
        sa.PrimaryKeyConstraint(
            "list_project",
            "list_id",
            "consumer_project",
            "consumer_form",
            name=op.f("pk_listconsumer"),
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )


def downgrade():
    op.drop_table("listconsumer")
    op.drop_table("publishedlistcolumn")
    op.drop_table("publishedlist")
