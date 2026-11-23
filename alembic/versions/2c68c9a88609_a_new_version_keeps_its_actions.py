"""A new version of a form keeps the actions of the version it replaces

Revision ID: 2c68c9a88609
Revises: 724e9ef39967
Create Date: 2026-11-21

A merge carried a follow-up's case links and properties over to the new
version and left its actions behind (propertyaction rows and the composed
odkform.action_module are kept per version), so the version that receives
the follow-ups changed no case. A version now gets them when mergeversions
accepts it (inherit_actions in processes/db/actions.py, called by
RepositoryMergeForm), not at upload: a version in testing has no dictionary,
and its rules would read as naming fields it lacks.

This repairs the versions merged before: each version with a parent in its
project and a repository (form_schema, which the merge gives it), oldest
first so that a chain of versions passes them along, gets a copy of its
parent's actions and module when it has no action of its own. A version
still in testing is left alone: its merge copies them. A version that has
actions, whoever added them, is left as it is. Each version repaired is
named in the output.

Nothing is undone on a downgrade: a copied action cannot be told from one
added by hand.
"""

import uuid

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2c68c9a88609"
down_revision = "724e9ef39967"
branch_labels = None
depends_on = None

COLUMNS = (
    "action_order, action_kind, action_code, action_desc, target_scope, "
    "target_kind, target_name, value_kind, value, when_rules, action_cdate"
)


def upgrade():
    conn = op.get_bind()
    versions = conn.execute(
        sa.text(
            "SELECT project_id, form_id, parent_form FROM odkform "
            "WHERE parent_form IS NOT NULL AND parent_project = project_id "
            "AND form_schema IS NOT NULL "
            "ORDER BY form_cdate, form_id"
        )
    ).fetchall()
    for project_id, form_id, parent_form in versions:
        own = conn.execute(
            sa.text(
                "SELECT COUNT(*) FROM propertyaction "
                "WHERE project_id = :project AND form_id = :form"
            ),
            {"project": project_id, "form": form_id},
        ).scalar()
        if own:
            continue
        rows = conn.execute(
            sa.text(
                "SELECT " + COLUMNS + " FROM propertyaction "
                "WHERE project_id = :project AND form_id = :form "
                "ORDER BY action_order"
            ),
            {"project": project_id, "form": parent_form},
        ).fetchall()
        if not rows:
            continue
        for a_row in rows:
            values = dict(zip([c.strip() for c in COLUMNS.split(",")], a_row))
            values.update(
                {
                    "action_id": str(uuid.uuid4()),
                    "project": project_id,
                    "form": form_id,
                }
            )
            conn.execute(
                sa.text(
                    "INSERT INTO propertyaction (action_id, project_id, form_id, "
                    + COLUMNS
                    + ") VALUES (:action_id, :project, :form, :action_order, "
                    ":action_kind, :action_code, :action_desc, :target_scope, "
                    ":target_kind, :target_name, :value_kind, :value, "
                    ":when_rules, :action_cdate)"
                ),
                values,
            )
        conn.execute(
            sa.text(
                "UPDATE odkform child JOIN odkform parent "
                "ON parent.project_id = child.project_id "
                "AND parent.form_id = :parent "
                "SET child.action_module = parent.action_module, "
                "child.action_mode = parent.action_mode "
                "WHERE child.project_id = :project AND child.form_id = :form"
            ),
            {"parent": parent_form, "project": project_id, "form": form_id},
        )
        print(
            "Form {} of project {} took the {} actions of the version it "
            "replaces, {}".format(form_id, project_id, len(rows), parent_form)
        )


def downgrade():
    pass
