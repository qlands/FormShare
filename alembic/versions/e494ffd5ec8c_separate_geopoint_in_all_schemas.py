"""Separate geopoint in all schemas

Revision ID: e494ffd5ec8c
Revises: 7a31fe6e7d09
Create Date: 2020-04-21 11:38:25.184496

"""

from alembic import op
from formshare.models.formshare import Odkform
from sqlalchemy.orm.session import Session

# revision identifiers, used by Alembic.
revision = "e494ffd5ec8c"
down_revision = "7a31fe6e7d09"
branch_labels = None
depends_on = None


def upgrade():
    session = Session(bind=op.get_bind())
    conn = op.get_bind()
    forms = (
        session.query(Odkform.form_schema).filter(Odkform.form_schema.isnot(None)).all()
    )
    for a_form in forms:
        try:
            conn.execute(
                "SELECT _longitude FROM {}.maintable".format(a_form.form_schema)
            )
        except Exception as e:
            if str(e).index("Unknown column") >= 0:
                conn.execute(
                    "ALTER TABLE {}.maintable ADD COLUMN _longitude double".format(
                        a_form.form_schema
                    )
                )
                conn.execute(
                    "ALTER TABLE {}.maintable ADD COLUMN _latitude double".format(
                        a_form.form_schema
                    )
                )
                conn.execute(
                    "ALTER TABLE {}.maintable ADD COLUMN _elevation decimal(9,3)".format(
                        a_form.form_schema
                    )
                )
                conn.execute(
                    "ALTER TABLE {}.maintable ADD COLUMN _precision decimal(9,3)".format(
                        a_form.form_schema
                    )
                )
                res = conn.execute(
                    "SELECT rowuuid,_geopoint FROM {}.maintable WHERE _geopoint IS NOT NULL".format(
                        a_form.form_schema
                    )
                )
                for a_record in res:
                    parts = a_record[1].split(" ")
                    longitude = "null"
                    latitude = "null"
                    elevation = "null"
                    precision = "null"
                    if len(parts) >= 4:
                        latitude = parts[0]
                        longitude = parts[1]
                        elevation = parts[2]
                        precision = parts[3]
                    else:
                        if len(parts) == 3:
                            latitude = parts[0]
                            longitude = parts[1]
                            elevation = parts[2]
                        else:
                            if len(parts) == 2:
                                latitude = parts[0]
                                longitude = parts[1]
                    try:
                        conn.execute(
                            "UPDATE {}.maintable SET _longitude = {}, _latitude = {}, _elevation = {}, "
                            "_precision = {} WHERE rowuuid = '{}'".format(
                                a_form.form_schema,
                                longitude,
                                latitude,
                                elevation,
                                precision,
                                a_record[0],
                            )
                        )
                    except Exception as e:
                        print(str(e))

    session.commit()


def downgrade():
    print("No downgrade necessary")
