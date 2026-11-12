"""A form being deleted keeps the ID of its deletion's task

Revision ID: 724e9ef39967
Revises: 7b4e1d09c3a2
Create Date: 2026-11-11

The project's page and the dashboard showed a form being deleted until they
were refreshed by hand. Now (owner, 2026-11-11) the request that deletes a
form stores the ID of the Celery task that deletes it on the form and its
versions, the task says on that ID's stream when it ends
(send_task_status_to_form), and the pages listening to it refresh, as they
do for an export.

- odkform.form_deletetask: the ID of the task deleting the form, from the
  request to the end of the task.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "724e9ef39967"
down_revision = "7b4e1d09c3a2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("odkform", sa.Column("form_deletetask", sa.Unicode(64)))


def downgrade():
    op.drop_column("odkform", "form_deletetask")
