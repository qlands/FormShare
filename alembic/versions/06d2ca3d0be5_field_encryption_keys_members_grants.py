"""Field encryption: project keys, members, unlock methods, grants, events

Revision ID: 06d2ca3d0be5
Revises: a7d2e9f4c1b8
Create Date: 2026-10-11

docs/formshare_field_encryption/ (formshare.md section 2). Answers to
questions a form marks fs_encrypted are sealed to the project's public key the
moment they arrive, and opened only in the browser of a member allowed to read
them. The server keeps what that needs and nothing that opens anything: the
public half of every version of a project's key, the public key of every
member, each member's private key as its browser locked it, the grants -- a
project key sealed in a browser to a member -- and the record of who did what.

Every date is kept to the microsecond: the record, the unlock methods and
the key versions are read in the order they happened, which a second does
not tell apart.

Four invariants are the database's, not only the code's, because a second
active key or member would split what a project can read: one active key per
project, one active member per user, per assistant and per project's recovery
kit. MySQL has no partial unique index; a functional one over an expression
that is NULL for the rows that do not count does the same (8.0.13 and later).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import DATETIME, MEDIUMTEXT

# revision identifiers, used by Alembic.
revision = "06d2ca3d0be5"
down_revision = "a7d2e9f4c1b8"
branch_labels = None
depends_on = None

_TABLE = dict(
    mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci", mysql_engine="InnoDB"
)

_ONE_ACTIVE = (
    (
        "ux_encryption_project_key_active",
        "encryption_project_key",
        "IF(key_status = 'active', project_id, NULL)",
    ),
    (
        "ux_encryption_member_user",
        "encryption_member",
        "IF(revoked_date IS NULL, user_id, NULL)",
    ),
    (
        "ux_encryption_member_assistant",
        "encryption_member",
        "IF(revoked_date IS NULL, coll_uuid, NULL)",
    ),
    (
        "ux_encryption_member_recovery",
        "encryption_member",
        "IF(revoked_date IS NULL AND member_type = 'recovery', project_id, NULL)",
    ),
)


def upgrade():
    op.create_table(
        "encryption_project_key",
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("key_id", sa.Unicode(length=16), nullable=False),
        sa.Column("public_key", sa.Unicode(length=100), nullable=False),
        sa.Column("key_status", sa.Unicode(length=10), nullable=False),
        sa.Column("created_by", sa.Unicode(length=120), nullable=True),
        sa.Column("created_date", DATETIME(fsp=6), nullable=True),
        sa.Column("retired_date", DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            name=op.f("fk_encryption_project_key_project_id_project"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "key_id", name=op.f("pk_encryption_project_key")
        ),
        **_TABLE
    )
    op.create_table(
        "encryption_member",
        sa.Column("member_id", sa.Unicode(length=64), nullable=False),
        sa.Column("member_type", sa.Unicode(length=10), nullable=False),
        sa.Column("user_id", sa.Unicode(length=120), nullable=True),
        sa.Column("coll_uuid", sa.Unicode(length=120), nullable=True),
        sa.Column("project_id", sa.Unicode(length=64), nullable=True),
        sa.Column("public_key", sa.Unicode(length=100), nullable=False),
        sa.Column("created_date", DATETIME(fsp=6), nullable=True),
        sa.Column("revoked_date", DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["fsuser.user_id"],
            name=op.f("fk_encryption_member_user_id_fsuser"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["coll_uuid"],
            ["collaborator.coll_uuid"],
            name=op.f("fk_encryption_member_coll_uuid_collaborator"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            name=op.f("fk_encryption_member_project_id_project"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("member_id", name=op.f("pk_encryption_member")),
        **_TABLE
    )
    for column in ("user_id", "coll_uuid", "project_id"):
        op.create_index(
            op.f("ix_encryption_member_" + column), "encryption_member", [column]
        )
    op.create_table(
        "encryption_unlock",
        sa.Column("unlock_id", sa.Unicode(length=64), nullable=False),
        sa.Column("member_id", sa.Unicode(length=64), nullable=False),
        sa.Column("unlock_method", sa.Unicode(length=10), nullable=False),
        sa.Column("unlock_label", sa.Unicode(length=120), nullable=True),
        sa.Column("credential_id", sa.Unicode(length=1400), nullable=True),
        sa.Column(
            "unlock_params", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
        sa.Column(
            "locked_key", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=False
        ),
        sa.Column("created_date", DATETIME(fsp=6), nullable=True),
        sa.Column("last_used_date", DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["encryption_member.member_id"],
            name=op.f("fk_encryption_unlock_member_id_encryption_member"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("unlock_id", name=op.f("pk_encryption_unlock")),
        **_TABLE
    )
    op.create_index(
        op.f("ix_encryption_unlock_member_id"), "encryption_unlock", ["member_id"]
    )
    op.create_table(
        "encryption_grant",
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("key_id", sa.Unicode(length=16), nullable=False),
        sa.Column("member_id", sa.Unicode(length=64), nullable=False),
        sa.Column(
            "grant_value", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=False
        ),
        sa.Column("granted_by", sa.Unicode(length=64), nullable=True),
        sa.Column("granted_date", DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id", "key_id"],
            ["encryption_project_key.project_id", "encryption_project_key.key_id"],
            name=op.f("fk_encryption_grant_project_id_encryption_project_key"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["encryption_member.member_id"],
            name=op.f("fk_encryption_grant_member_id_encryption_member"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", "key_id", "member_id", name=op.f("pk_encryption_grant")
        ),
        **_TABLE
    )
    op.create_index(
        op.f("ix_encryption_grant_member_id"), "encryption_grant", ["member_id"]
    )
    op.create_table(
        "encryption_event",
        sa.Column("event_id", sa.Unicode(length=64), nullable=False),
        sa.Column("project_id", sa.Unicode(length=64), nullable=True),
        sa.Column("actor_type", sa.Unicode(length=10), nullable=False),
        sa.Column("actor_id", sa.Unicode(length=120), nullable=True),
        sa.Column("event_type", sa.Unicode(length=30), nullable=False),
        sa.Column(
            "event_detail", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
        sa.Column("event_date", DATETIME(fsp=6), nullable=False),
        sa.Column("ip", sa.Unicode(length=45), nullable=True),
        sa.Column("user_agent", sa.Unicode(length=512), nullable=True),
        sa.PrimaryKeyConstraint("event_id", name=op.f("pk_encryption_event")),
        **_TABLE
    )
    op.create_index(
        "ix_encryption_event_project", "encryption_event", ["project_id", "event_date"]
    )
    for name, table, expression in _ONE_ACTIVE:
        op.execute(
            "CREATE UNIQUE INDEX {} ON {} (({}))".format(name, table, expression)
        )


def downgrade():
    op.drop_table("encryption_event")
    op.drop_table("encryption_grant")
    op.drop_table("encryption_unlock")
    op.drop_table("encryption_member")
    op.drop_table("encryption_project_key")
