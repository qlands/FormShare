"""formshare_encrypted marks a field sensitive, not encrypted

Revision ID: 4e0b5cb46d1a
Revises: 06d2ca3d0be5
Create Date: 2026-10-11

Until field encryption, the XLSForm column formshare_encrypted set
dictfield.field_encrypted, and the dictionary showed such a field as
"Sensitive - Protection type: encrypted" while its answers were stored in
clear. field_encrypted now says that a column holds envelopes -- create.xml's
fs_encrypted, written by RSTools -- and the Encryption plugin opens the
columns it marks (docs/formshare_field_encryption/formshare.md 6.4 and 6.5).

No column held an envelope before this revision: RSTools had no fs_encrypted.
So every row marked so far is a formshare_encrypted one, and it becomes what
the dictionary showed: sensitive, with the protection a build now gives such
a field (exclude; recode for a key), and no longer claiming encryption.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4e0b5cb46d1a"
down_revision = "06d2ca3d0be5"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "UPDATE dictfield SET field_sensitive = 1, "
        "field_protection = COALESCE(field_protection, "
        "IF(field_key = 1, 'recode', 'exclude')), field_encrypted = 0 "
        "WHERE field_encrypted = 1"
    )


def downgrade():
    # Which sensitive fields were formshare_encrypted ones cannot be told
    # apart again, and claiming encryption for clear answers is what this
    # revision ended.
    pass
