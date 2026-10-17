"""A list may serve each assistant their own cases

Revision ID: 1a23426f5191
Revises: 900a9accc6d7
Create Date: 2026-10-17

Feature 7 of docs/formshare_case_management/ (formshare.md 3.8, stage 8). A
published list in a mode other than "all" is served to each assistant as a
variant: the list's SELECT with a clause of theirs ANDed in. listvariant
records each variant that has been generated -- named by the MD5 of its
clause, so assistants with the same clause share one -- with the MD5 of its
file and when it was generated. publishedlist.list_filter_mode, which says
the mode, has been there since the registry; nothing to convert: every list
is in mode "all".
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1a23426f5191"
down_revision = "900a9accc6d7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "listvariant",
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("list_id", sa.Unicode(length=120), nullable=False),
        sa.Column("variant_key", sa.Unicode(length=32), nullable=False),
        sa.Column("variant_md5", sa.Unicode(length=32), nullable=True),
        sa.Column("variant_lastgen", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id", "list_id"],
            ["publishedlist.project_id", "publishedlist.list_id"],
            name=op.f("fk_listvariant_project_id_publishedlist"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "list_id", "variant_key", name=op.f("pk_listvariant")
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )


def downgrade():
    op.drop_table("listvariant")
