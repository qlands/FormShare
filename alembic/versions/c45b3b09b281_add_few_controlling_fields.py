"""Add few controlling fields

Revision ID: c45b3b09b281
Revises: 6e8f0f158657
Create Date: 2026-04-18 07:33:03.983645

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c45b3b09b281"
down_revision = "6e8f0f158657"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "fsuser",
        sa.Column(
            "user_max_projects",
            sa.INTEGER(),
            server_default=sa.text("'1'"),
            nullable=True,
        ),
    )
    op.add_column(
        "fsuser",
        sa.Column(
            "user_kb_used",
            sa.DECIMAL(precision=14, scale=3),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    op.add_column(
        "fsuser",
        sa.Column(
            "user_in_files_kb_used",
            sa.DECIMAL(precision=14, scale=3),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    op.add_column(
        "fsuser", sa.Column("user_in_files_last_event", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "fsuser", sa.Column("user_in_files_last_read", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "project",
        sa.Column(
            "project_archiving",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    op.add_column(
        "project",
        sa.Column(
            "project_restoring",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("project", "project_restoring")
    op.drop_column("project", "project_archiving")
    op.drop_column("fsuser", "user_in_files_last_read")
    op.drop_column("fsuser", "user_in_files_last_event")
    op.drop_column("fsuser", "user_in_files_kb_used")
    op.drop_column("fsuser", "user_kb_used")
    op.drop_column("fsuser", "user_max_projects")
