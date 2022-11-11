"""Update XML files in database

Revision ID: 135c7989d4b0
Revises: b735d4dd5fb7
Create Date: 2020-11-21 17:20:50.820488

"""
import os

from alembic import context
from alembic import op
from formshare.models.formshare import Odkform
from pyramid.paster import get_appsettings, setup_logging
from sqlalchemy.orm.session import Session

# revision identifiers, used by Alembic.
revision = "135c7989d4b0"
down_revision = "b735d4dd5fb7"
branch_labels = None
depends_on = None


def upgrade():
    config_uri = context.config.get_main_option("formshare.ini.file", None)
    if config_uri is None:
        print(
            "This migration needs parameter 'formshare.ini.file' in the alembic ini file."
        )
        print(
            "The parameter 'formshare.ini.file' must point to the full path of the FormShare ini file"
        )
        exit(1)

    setup_logging(config_uri)
    settings = get_appsettings(config_uri, "formshare")
    repository_path = settings["repository.path"]
    session = Session(bind=op.get_bind())
    forms = (
        session.query(Odkform.form_directory, Odkform.project_id, Odkform.form_id)
        .filter(Odkform.form_createxmlfile.is_(None))
        .all()
    )
    for a_form in forms:
        create_xml_file = os.path.join(
            repository_path,
            *["odk", "forms", a_form.form_directory, "repository", "create.xml"]
        )
        session.query(Odkform.form_createxmlfile).filter(
            Odkform.project_id == a_form.project_id
        ).filter(Odkform.form_id == a_form.form_id).update(
            {"form_createxmlfile": create_xml_file}
        )

    forms = (
        session.query(Odkform.form_createxmlfile, Odkform.project_id, Odkform.form_id)
        .filter(Odkform.form_insertxmlfile.is_(None))
        .all()
    )
    for a_form in forms:
        insert_file = a_form.form_createxmlfile.replace("create.xml", "insert.xml")
        session.query(Odkform.form_insertxmlfile).filter(
            Odkform.project_id == a_form.project_id
        ).filter(Odkform.form_id == a_form.form_id).update(
            {"form_insertxmlfile": insert_file}
        )

    session.commit()


def downgrade():
    # Nothing to downgrade
    pass
