"""A project may have a logo

Revision ID: 900a9accc6d7
Revises: 774795fe26e2
Create Date: 2026-10-14

FormShare Collect shows a project's logo on its main menu
(docs/project-logo.md). The image is kept in the project's storage under one
name; this column holds its MD5, which says whether there is one and which,
and goes into the project's QR and into every form's manifest. Nothing to
convert: no project has a logo yet.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "900a9accc6d7"
down_revision = "774795fe26e2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "project", sa.Column("project_logo_md5", sa.Unicode(length=32), nullable=True)
    )


def downgrade():
    op.drop_column("project", "project_logo_md5")
