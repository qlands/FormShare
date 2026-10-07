"""What a run's changed columns held, exactly, for its take-back

Revision ID: d3a9f6c1b2e4
Revises: b4f1d8e2c6a7
Create Date: 2026-10-07

RSTools' answer to the server's take-back (docs/formshare_case_management/
rstools.md 24.1). The change report spells an old value as JavaScript does,
from the double the module was handed, and a decimal(17,3) with thirteen or
fourteen digits before the point does not come back from a double: put back
from the report, its last digits could differ from what was stored, or not
fit the column at all. actionrun.run_restore keeps each changed column as
MySQL spells it, read when the writes are planned, beside the report rather
than in it. Runs recorded before have none and are taken back as before.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

# revision identifiers, used by Alembic.
revision = "d3a9f6c1b2e4"
down_revision = "b4f1d8e2c6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "actionrun",
        sa.Column(
            "run_restore", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
    )


def downgrade():
    op.drop_column("actionrun", "run_restore")
