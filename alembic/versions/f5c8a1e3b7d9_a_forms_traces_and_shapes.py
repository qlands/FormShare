"""The geotraces and geoshapes of a form, for the map

Revision ID: f5c8a1e3b7d9
Revises: d3a9f6c1b2e4
Create Date: 2026-10-07

The map drew a submission by its form's first geopoint only, recorded at
upload in odkform.form_geopoint, so a submission located by a geotrace or a
geoshape was not on it at all. odkform.form_geoshape records those variables
the same way -- the main table's, in form order, as "group/name:type" -- and
the indexing gives the dataset index a shape to draw from them
(processes/geometry.py).

Existing forms are backfilled from the survey JSON they were uploaded with. A
form whose file is no longer on disk is named in the output: its new
submissions will be drawn by their geopoint only until it is uploaded again.
Submissions indexed before keep their old document until they are indexed
again (index_geometries).
"""

import json
import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import MEDIUMTEXT

# revision identifiers, used by Alembic.
revision = "f5c8a1e3b7d9"
down_revision = "d3a9f6c1b2e4"
branch_labels = None
depends_on = None


def _shape_variables(json_dict):
    # The walk of processes/geometry.py's geoshape_variables_of as it is
    # today, kept here so that the migration does not change if it does.
    found = []

    def walk(node, path):
        node_type = node.get("type")
        if node_type in ("survey", "group"):
            if node_type == "group":
                path = path + [node["name"]]
            for child in node.get("children", []):
                walk(child, path)
        elif node_type in ("geotrace", "geoshape"):
            found.append("/".join(path + [node["name"]]) + ":" + node_type)

    walk(json_dict, [])
    return found


def upgrade():
    op.add_column(
        "odkform",
        sa.Column(
            "form_geoshape", MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
    )
    connection = op.get_bind()
    forms = connection.execute(
        sa.text(
            "SELECT project_id, form_id, form_jsonfile FROM odkform "
            "WHERE form_jsonfile IS NOT NULL"
        )
    ).fetchall()
    unreadable = []
    with_shapes = 0
    for project_id, form_id, json_file in forms:
        try:
            with open(json_file, encoding="utf-8") as a_file:
                variables = _shape_variables(json.load(a_file))
        except Exception as e:
            unreadable.append(
                "{}/{} ({})".format(
                    project_id,
                    form_id,
                    "no file" if not os.path.isfile(json_file) else str(e),
                )
            )
            continue
        if variables:
            with_shapes += 1
            connection.execute(
                sa.text(
                    "UPDATE odkform SET form_geoshape = :v "
                    "WHERE project_id = :p AND form_id = :f"
                ),
                {"v": ",".join(variables), "p": project_id, "f": form_id},
            )
    print(
        "form_geoshape: {} form(s) with a trace or a shape, of {}".format(
            with_shapes, len(forms)
        )
    )
    if unreadable:
        print(
            "form_geoshape: the survey of these forms could not be read: "
            + "; ".join(unreadable)
        )


def downgrade():
    op.drop_column("odkform", "form_geoshape")
