"""Actions: the decision table, the module on the form, and the run log

Revision ID: 7c1e2a9d4b30
Revises: 54435174da06
Create Date: 2026-09-23

Feature 3 of docs/formshare_case_management/, decision 16: a form's actions
are one JavaScript module, compiled from the rows of its decision table
(propertyaction) or written in expert mode, kept on the form
(odkform.action_mode, odkform.action_module) and served as actions.json.
Every run on the server is recorded (actionrun): the changes it applied, or
the failure that left the submission loaded and waiting for a retry.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

# revision identifiers, used by Alembic.
revision = "7c1e2a9d4b30"
down_revision = "54435174da06"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "odkform",
        sa.Column(
            "action_mode",
            sa.Unicode(length=10),
            server_default=sa.text("'table'"),
            nullable=True,
        ),
    )
    op.add_column(
        "odkform",
        sa.Column(
            "action_module", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
    )
    op.create_table(
        "propertyaction",
        sa.Column("action_id", sa.Unicode(length=64), nullable=False),
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("form_id", sa.Unicode(length=120), nullable=False),
        sa.Column(
            "action_order",
            sa.Integer(),
            server_default=sa.text("'0'"),
            nullable=False,
        ),
        sa.Column(
            "target_scope",
            sa.Unicode(length=10),
            server_default=sa.text("'case'"),
            nullable=False,
        ),
        sa.Column("target_kind", sa.Unicode(length=10), nullable=False),
        sa.Column("target_name", sa.Unicode(length=120), nullable=True),
        sa.Column("value_kind", sa.Unicode(length=10), nullable=False),
        sa.Column("value", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True),
        sa.Column(
            "when_rules", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
        sa.Column("action_cdate", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            name=op.f("fk_propertyaction_form_id_odkform"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("action_id", name=op.f("pk_propertyaction")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_propertyaction_form",
        "propertyaction",
        ["project_id", "form_id", "action_order"],
    )
    op.create_table(
        "actionrun",
        sa.Column("run_id", sa.Unicode(length=64), nullable=False),
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("form_id", sa.Unicode(length=120), nullable=False),
        sa.Column("submission_id", sa.Unicode(length=64), nullable=True),
        sa.Column("main_rowuuid", sa.Unicode(length=80), nullable=False),
        sa.Column("run_dtime", sa.DateTime(), nullable=True),
        sa.Column(
            "run_status", sa.Integer(), server_default=sa.text("'0'"), nullable=False
        ),
        sa.Column(
            "run_message", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
        sa.Column(
            "run_changes", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
        sa.Column("run_log", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            name=op.f("fk_actionrun_form_id_odkform"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("run_id", name=op.f("pk_actionrun")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_actionrun_form", "actionrun", ["project_id", "form_id", "run_status"]
    )


def downgrade():
    op.drop_index("ix_actionrun_form", table_name="actionrun")
    op.drop_table("actionrun")
    op.drop_index("ix_propertyaction_form", table_name="propertyaction")
    op.drop_table("propertyaction")
    op.drop_column("odkform", "action_module")
    op.drop_column("odkform", "action_mode")
