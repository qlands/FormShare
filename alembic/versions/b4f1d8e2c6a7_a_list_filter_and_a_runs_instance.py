"""A list's filter as the owner built it, and a run's instanceID

Revision ID: b4f1d8e2c6a7
Revises: 7c1e2a9d4b30
Create Date: 2026-09-25

Two answers to the device's QA (docs/formshare_case_management/formshare.md
section 8). publishedlist.filter_rules keeps the filter of a published list
as the QueryBuilder rule set the owner built, from which filter_sql -- which
the list's SELECT already appended, and nothing wrote -- is compiled (8.1).
actionrun.instance_id keeps the submission's meta/instanceID beside the
server's own submission id, so a device can find the run of a submission it
sent (8.5). Runs recorded before have none; nothing can recover it.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

# revision identifiers, used by Alembic.
revision = "b4f1d8e2c6a7"
down_revision = "7c1e2a9d4b30"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "publishedlist",
        sa.Column("filter_rules", MEDIUMTEXT(), nullable=True),
    )
    op.add_column(
        "actionrun",
        sa.Column("instance_id", sa.Unicode(length=120), nullable=True),
    )


def downgrade():
    op.drop_column("actionrun", "instance_id")
    op.drop_column("publishedlist", "filter_rules")
