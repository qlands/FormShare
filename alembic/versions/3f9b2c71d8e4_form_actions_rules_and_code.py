"""Form actions: an action is a rule or code

Revision ID: 3f9b2c71d8e4
Revises: 89adc46b7aaa
Create Date: 2026-10-20

The actions page lists a form's actions, each a rule of the decision table
(When, Target, Value) or code its author wrote: what expert mode, a switch
for the whole form, used to hold (owner, 2026-10-20). FormShare composes them
into the one module the form serves (odkform.action_module), calling them
from the last to the first, so that the first one's change is kept when two
change the same thing.

- propertyaction.action_kind is rule or code, action_code is the code of a
  code action, and action_desc says what it does in its author's words. A
  code action has no target or value, so target_kind and value_kind may now
  be NULL.
- A form in expert mode gets one code action holding its module. Its rules
  were not running, so they go: no production user had written rules (the
  owner, 2026-10-20).
- odkform.action_module stays as it is, so every form still does what it
  did. It is composed again at the next change to the form's actions.
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

# revision identifiers, used by Alembic.
revision = "3f9b2c71d8e4"
down_revision = "89adc46b7aaa"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "propertyaction",
        sa.Column(
            "action_kind",
            sa.Unicode(length=10),
            server_default=sa.text("'rule'"),
            nullable=False,
        ),
    )
    op.add_column(
        "propertyaction",
        sa.Column(
            "action_code", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
    )
    op.add_column(
        "propertyaction",
        sa.Column("action_desc", sa.Unicode(length=255), nullable=True),
    )
    op.alter_column(
        "propertyaction",
        "target_kind",
        existing_type=sa.Unicode(length=10),
        nullable=True,
    )
    op.alter_column(
        "propertyaction",
        "value_kind",
        existing_type=sa.Unicode(length=10),
        nullable=True,
    )
    connection = op.get_bind()
    expert = connection.execute(
        sa.text(
            "SELECT project_id, form_id, action_module FROM odkform "
            "WHERE action_mode = 'expert'"
        )
    ).fetchall()
    for project_id, form_id, module in expert:
        connection.execute(
            sa.text(
                "DELETE FROM propertyaction WHERE project_id = :p AND form_id = :f"
            ),
            {"p": project_id, "f": form_id},
        )
        if module is None or module.strip() == "":
            continue
        connection.execute(
            sa.text(
                "INSERT INTO propertyaction (action_id, project_id, form_id, "
                "action_order, action_kind, action_code, target_scope, "
                "action_cdate) VALUES (:a, :p, :f, 1, 'code', :c, 'case', NOW())"
            ),
            {"a": str(uuid.uuid4()), "p": project_id, "f": form_id, "c": module},
        )


def downgrade():
    # Back to one mode per form: a form whose actions include code is in
    # expert mode with its module as composed, and code actions go.
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE odkform SET action_mode = 'expert' WHERE EXISTS (SELECT 1 "
            "FROM propertyaction a WHERE a.project_id = odkform.project_id AND "
            "a.form_id = odkform.form_id AND a.action_kind = 'code')"
        )
    )
    connection.execute(sa.text("DELETE FROM propertyaction WHERE action_kind = 'code'"))
    op.alter_column(
        "propertyaction",
        "value_kind",
        existing_type=sa.Unicode(length=10),
        nullable=False,
    )
    op.alter_column(
        "propertyaction",
        "target_kind",
        existing_type=sa.Unicode(length=10),
        nullable=False,
    )
    op.drop_column("propertyaction", "action_desc")
    op.drop_column("propertyaction", "action_code")
    op.drop_column("propertyaction", "action_kind")
