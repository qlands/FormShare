"""Add offline entities flag to project

Revision ID: a3e17c94b210
Revises: d90cdbd36cae
Create Date: 2026-08-15 09:40:00.000000

A project with this set serves its case list to ODK clients as an entity list,
so a case registered offline can be followed up before the device syncs. It is
off for every existing project on purpose: turning it on changes what a
follow-up form stores as its selector, and it needs a repository built by a
version of RSTools that skips the entity declaration and mints v4 rowuuids.

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a3e17c94b210"
down_revision = "d90cdbd36cae"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "project",
        sa.Column(
            "project_entities",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("project", "project_entities")
