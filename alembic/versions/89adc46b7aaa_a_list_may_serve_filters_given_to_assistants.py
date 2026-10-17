"""A list may serve the cases of filters given to assistants and groups

Revision ID: 89adc46b7aaa
Revises: 1a23426f5191
Create Date: 2026-10-17

Feature 7 of docs/formshare_case_management/ (formshare.md 3.8, stage 8), its
third mode. A list in mode "filters" has named filters (listfilter): the
owner's QueryBuilder rules and the SQL compiled from them, as the list's own
filter. Each is given to assistants and groups (listfilterassignee), who
receive the cases it matches. Nothing to convert: no list is in that mode.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

# revision identifiers, used by Alembic.
revision = "89adc46b7aaa"
down_revision = "1a23426f5191"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "listfilter",
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("list_id", sa.Unicode(length=120), nullable=False),
        sa.Column("filter_id", sa.Unicode(length=64), nullable=False),
        sa.Column("filter_name", sa.Unicode(length=120), nullable=False),
        sa.Column("filter_rules", MEDIUMTEXT(), nullable=True),
        sa.Column("filter_sql", MEDIUMTEXT(), nullable=True),
        sa.Column("filter_cdate", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id", "list_id"],
            ["publishedlist.project_id", "publishedlist.list_id"],
            name=op.f("fk_listfilter_project_id_publishedlist"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "list_id", "filter_id", name=op.f("pk_listfilter")
        ),
        sa.UniqueConstraint(
            "project_id",
            "list_id",
            "filter_name",
            name=op.f("uq_listfilter_project_id"),
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "listfilterassignee",
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("list_id", sa.Unicode(length=120), nullable=False),
        sa.Column("filter_id", sa.Unicode(length=64), nullable=False),
        sa.Column("assignee_type", sa.Unicode(length=10), nullable=False),
        sa.Column("assignee_id", sa.Unicode(length=120), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "list_id", "filter_id"],
            ["listfilter.project_id", "listfilter.list_id", "listfilter.filter_id"],
            name=op.f("fk_listfilterassignee_project_id_listfilter"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id",
            "list_id",
            "filter_id",
            "assignee_type",
            "assignee_id",
            name=op.f("pk_listfilterassignee"),
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )


def downgrade():
    op.drop_table("listfilterassignee")
    op.drop_table("listfilter")
