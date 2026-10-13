"""A version of a project's key is signed, and so is every grant of it

Revision ID: 774795fe26e2
Revises: 4e0b5cb46d1a
Create Date: 2026-10-13

A rotation used to ask only for the owner's session: whoever had it -- a
stolen cookie, a script on a page -- could put in a key pair of their own,
with genuine grants for every holder, and read every answer sealed after.
Anyone who could write the database could do the same without the session,
and no vault would notice (docs/formshare_field_encryption/formshare.md 13.1).

Each version now has a signing key, derived in a browser from its private
key, and is vouched for by the version it replaced: the signature and the
signing key are stored here. The server checks them at every write that
carries key material, and a vault checks the chain at every unlock
(README 3.6).

Nothing is converted. No version could be signed without its private key,
which the server never has, so a key set up before this revision keeps NULL
in the three columns, and core refuses to rotate it, to grant it or to give
it a new recovery kit until encryption is set up again. Field encryption had
not reached production when this revision was written.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "774795fe26e2"
down_revision = "4e0b5cb46d1a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "encryption_project_key",
        sa.Column("sign_public_key", sa.Unicode(length=100), nullable=True),
    )
    op.add_column(
        "encryption_project_key",
        sa.Column("signed_by", sa.Unicode(length=16), nullable=True),
    )
    op.add_column(
        "encryption_project_key",
        sa.Column("key_signature", sa.Unicode(length=100), nullable=True),
    )


def downgrade():
    op.drop_column("encryption_project_key", "key_signature")
    op.drop_column("encryption_project_key", "signed_by")
    op.drop_column("encryption_project_key", "sign_public_key")
