"""Add blob storage for projects

Revision ID: 97cf65221719
Revises: f8cfdffd5344
Create Date: 2026-07-27 12:49:50.581156

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "97cf65221719"
down_revision = "f8cfdffd5344"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "project",
        sa.Column(
            "project_blob_storage",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("project", "project_blob_storage")
