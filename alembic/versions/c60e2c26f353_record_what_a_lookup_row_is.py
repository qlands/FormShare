"""Record what a lookup row is in the field dictionary

Revision ID: c60e2c26f353
Revises: a3e17c94b210
Create Date: 2026-08-26 10:00:00.000000

Schema format 3.0 changed the shape of a lookup table three times over. A form
that declares allow_choice_duplicates gets lookups keyed by an autoincrement
surrogate instead of by their code, so the code alone no longer names a row.
The columns that tell two choices sharing a code apart are named in rfilter, on
the field that references the lookup. And a GeoJSON lookup carries a geometry
column MySQL derives for itself and refuses to be given a value for.

The dictionary recorded none of it, so a replaced CSV or GeoJSON had nothing to
key its merge on and no way to know which columns it must not write. These five
columns carry those attributes across from create.xml.

Existing forms are backfilled from the create.xml they were built from. A form
whose create.xml is no longer on disk keeps the defaults and is named in the
output: its lookups will merge on the code alone until the file is back.

"""

import os

import sqlalchemy as sa
from alembic import op
from lxml import etree
from sqlalchemy.orm.session import Session

from formshare.models.formshare import Odkform

# revision identifiers, used by Alembic.
revision = "c60e2c26f353"
down_revision = "a3e17c94b210"
branch_labels = None
depends_on = None

NEW_COLUMNS = [
    "field_rfilter",
    "field_generatedas",
    "field_autoincrement",
    "field_notnull",
    "field_srid",
]


def field_values(a_field):
    """The 3.0 attributes of one field of a create.xml, or None if it has none.

    A field that declares none of them is left alone rather than written with
    defaults it already has.
    """
    values = {
        "field_rfilter": a_field.get("rfilter"),
        "field_generatedas": a_field.get("generatedas"),
        "field_autoincrement": 1 if a_field.get("autoincrement") == "true" else 0,
        "field_notnull": 1 if a_field.get("notnull") == "true" else 0,
        "field_srid": a_field.get("srid"),
    }
    if (
        values["field_rfilter"] is None
        and values["field_generatedas"] is None
        and values["field_srid"] is None
        and values["field_autoincrement"] == 0
        and values["field_notnull"] == 0
    ):
        return None
    return values


def upgrade():
    op.add_column("dictfield", sa.Column("field_rfilter", sa.Unicode(1024)))
    op.add_column("dictfield", sa.Column("field_generatedas", sa.UnicodeText()))
    op.add_column(
        "dictfield",
        sa.Column("field_autoincrement", sa.INTEGER(), server_default=sa.text("'0'")),
    )
    op.add_column(
        "dictfield",
        sa.Column("field_notnull", sa.INTEGER(), server_default=sa.text("'0'")),
    )
    op.add_column("dictfield", sa.Column("field_srid", sa.Unicode(64)))

    session = Session(bind=op.get_bind())
    update = sa.text(
        "UPDATE dictfield SET "
        + ", ".join("{0} = :{0}".format(column) for column in NEW_COLUMNS)
        + " WHERE project_id = :project_id AND form_id = :form_id"
        " AND table_name = :table_name AND field_name = :field_name"
    )

    forms = (
        session.query(Odkform.project_id, Odkform.form_id, Odkform.form_createxmlfile)
        .filter(Odkform.form_createxmlfile.isnot(None))
        .all()
    )
    without_create_file = []
    updated = 0
    for a_form in forms:
        if not os.path.isfile(a_form.form_createxmlfile):
            without_create_file.append(
                "{}/{}".format(a_form.project_id, a_form.form_id)
            )
            continue
        try:
            root = etree.parse(a_form.form_createxmlfile).getroot()
        except Exception as e:
            without_create_file.append(
                "{}/{} ({})".format(a_form.project_id, a_form.form_id, str(e))
            )
            continue
        for a_table in root.findall(".//table"):
            for a_field in a_table.findall("field"):
                values = field_values(a_field)
                if values is None:
                    continue
                values["project_id"] = a_form.project_id
                values["form_id"] = a_form.form_id
                values["table_name"] = a_table.get("name")
                values["field_name"] = a_field.get("name")
                updated += session.execute(update, values).rowcount
    session.commit()

    print("Backfilled {} dictionary fields from create.xml".format(updated))
    if without_create_file:
        print(
            "These forms have no readable create.xml. Their lookups will merge a "
            "replaced file on the code alone until it is back:"
        )
        for a_form in without_create_file:
            print("\t" + a_form)


def downgrade():
    for column in NEW_COLUMNS:
        op.drop_column("dictfield", column)
