"""A form is deleted in the background

Revision ID: 7b4e1d09c3a2
Revises: 3f9b2c71d8e4
Create Date: 2026-10-28

Deleting a form used to delete its row in the request, rename its directory
and leave its repository in MySQL. Now (owner, 2026-10-28) the request asks
the form's ID to be typed, marks the form inactive, blocked and being
deleted, and queues a Celery task that keeps a gzipped dump of the
repository in the form's directory, drops the repository, renames the
directory and deletes the form and its versions. Users cannot cancel it; a
deletion that stops is resumed on the server by the technical team
(resume_form_deletion).

- odkform.form_deleting: 1 from the request to the end of the task;
- odkform.form_deletedby: who asked, as the renamed directory names them;
- odkform.form_deleteerror: why the task stopped.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

# revision identifiers, used by Alembic.
revision = "7b4e1d09c3a2"
down_revision = "3f9b2c71d8e4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "odkform",
        sa.Column(
            "form_deleting", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )
    op.add_column("odkform", sa.Column("form_deletedby", sa.Unicode(120)))
    op.add_column(
        "odkform",
        sa.Column("form_deleteerror", MEDIUMTEXT(collation="utf8mb4_unicode_ci")),
    )


def downgrade():
    op.drop_column("odkform", "form_deleteerror")
    op.drop_column("odkform", "form_deletedby")
    op.drop_column("odkform", "form_deleting")
