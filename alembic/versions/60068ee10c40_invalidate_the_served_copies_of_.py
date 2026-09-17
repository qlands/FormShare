"""Invalidate the served copies of published lists

Revision ID: 60068ee10c40
Revises: 1810d0dba954
Create Date: 2026-09-17

A form's copy of a published list is regenerated at manifest time only when
stale, and until 17d5f390 stale was decided against the source's data alone:
a column added to the list, or another label, filter, key or active flag, did
not count, so a form kept serving the old columns until the source next
received data. The edit view now clears the copies' generation stamp
(invalidate_list_copies), but a copy generated before that change, for a list
changed before it, still carries a stamp newer than the source's data and is
never regenerated: on the ECCE project the roster's school column was served
to no device.

This clears the stamp on every copy once. A copy is the media file named
after a list in the list's project, which is how the manifest finds them. The
next pull of each consuming form regenerates its copy; a copy whose content
did not change keeps its md5, so a device downloads nothing it already has.

The downgrade has nothing to restore: a cleared stamp is refilled by the next
pull.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "60068ee10c40"
down_revision = "1810d0dba954"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE mediafile m "
        "JOIN publishedlist l "
        "ON l.project_id = m.project_id AND l.list_filename = m.file_name "
        "SET m.file_lastgen = NULL"
    )


def downgrade():
    pass
