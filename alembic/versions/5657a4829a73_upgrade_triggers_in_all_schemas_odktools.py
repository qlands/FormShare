"""Upgrade triggers in all schemas. (ODKTools)

Revision ID: 5657a4829a73
Revises: 713b00eed9c9
Create Date: 2020-04-23 09:07:40.941358

"""
import os
import shutil
from subprocess import Popen, PIPE

from alembic import context
from alembic import op
from formshare.models.formshare import Odkform
from lxml import etree
from pyramid.paster import get_appsettings, setup_logging
from sqlalchemy.orm.session import Session

# revision identifiers, used by Alembic.
revision = "5657a4829a73"
down_revision = "713b00eed9c9"
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
    # ### end Alembic commands ###
    session = Session(bind=op.get_bind())
    forms = (
        session.query(Odkform.form_schema, Odkform.form_directory)
        .filter(Odkform.form_schema.isnot(None))
        .all()
    )
    my_cnf_file = settings.get("mysql.cnf")
    mysql_host = settings.get("mysql.host")
    mysql_port = settings.get("mysql.port", "3306")
    mysql_user = settings.get("mysql.user")
    mysql_password = settings.get("mysql.password")

    repository_directory = settings.get("repository.path", "")
    if repository_directory == "":
        print("Cannot find the repository path.")
        exit(1)
    for a_form in forms:
        parts = [
            "odk",
            "forms",
            a_form.form_directory,
            "repository",
            "mysql_create_audit.sql",
        ]
        create_file = os.path.join(repository_directory, *parts)
        parts = [
            "odk",
            "forms",
            a_form.form_directory,
            "repository",
            "mysql_drop_audit.sql",
        ]
        drop_file = os.path.join(repository_directory, *parts)
        if os.path.exists(create_file) and os.path.exists(drop_file):
            parts = ["odk", "forms", a_form.form_directory, "repository", "create.xml"]
            create_xml_file = os.path.join(repository_directory, *parts)

            parts = ["odk", "forms", a_form.form_directory, "repository"]
            form_repository_path = os.path.join(repository_directory, *parts)

            shutil.copyfile(create_file, create_file + ".5657a4829a73")
            shutil.copyfile(drop_file, drop_file + ".5657a4829a73")

            parser = etree.XMLParser(remove_blank_text=True)
            tree_create = etree.parse(create_xml_file, parser)
            root_create = tree_create.getroot()
            tables = root_create.findall(".//table")
            table_array = []
            if tables:
                for a_table in tables:
                    table_array.append(a_table.get("name"))

            create_audit_triggers = os.path.join(
                settings["odktools.path"],
                *["utilities", "createAuditTriggers", "createaudittriggers"]
            )

            args = [
                create_audit_triggers,
                "-H " + mysql_host,
                "-P " + mysql_port,
                "-u " + mysql_user,
                "-p " + mysql_password,
                "-s " + a_form.form_schema,
                "-o " + form_repository_path,
                "-t " + ",".join(table_array),
            ]
            p = Popen(args, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            if p.returncode == 0:
                args = ["mysql", "--defaults-file=" + my_cnf_file, a_form.form_schema]
                with open(drop_file + ".5657a4829a73") as input_drop_file:
                    proc = Popen(args, stdin=input_drop_file, stderr=PIPE, stdout=PIPE)
                    output, error = proc.communicate()
                    if proc.returncode == 0:
                        args = [
                            "mysql",
                            "--defaults-file=" + my_cnf_file,
                            a_form.form_schema,
                        ]
                        with open(create_file) as input_create_file:
                            proc = Popen(
                                args, stdin=input_create_file, stderr=PIPE, stdout=PIPE
                            )
                            output, error = proc.communicate()
                            if proc.returncode != 0:
                                print(
                                    "Cannot create new triggers for schema {} with file {}. Error:{}-{}".format(
                                        a_form.form_schema,
                                        create_file,
                                        output.decode(),
                                        error.decode(),
                                    )
                                )
                                exit(1)
                    else:
                        print(
                            "Cannot drop old triggers for schema {} with file {}. Error:{}-{}".format(
                                a_form.form_schema,
                                drop_file + ".5657a4829a73",
                                output.decode(),
                                error.decode(),
                            )
                        )
                        exit(1)
            else:
                print(
                    "Cannot create new triggers. Error: {}-{}".format(
                        stdout.decode(), stderr.decode()
                    )
                )
                exit(1)

    session.commit()


def downgrade():
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
    # ### end Alembic commands ###
    session = Session(bind=op.get_bind())
    forms = (
        session.query(Odkform.form_schema, Odkform.form_directory)
        .filter(Odkform.form_schema.isnot(None))
        .all()
    )
    my_cnf_file = settings.get("mysql.cnf")

    repository_directory = settings.get("repository.path", "")
    if repository_directory == "":
        print("Cannot find the repository path.")
        exit(1)
    for a_form in forms:
        parts = [
            "odk",
            "forms",
            a_form.form_directory,
            "repository",
            "mysql_create_audit.sql",
        ]
        create_file = os.path.join(repository_directory, *parts)
        parts = [
            "odk",
            "forms",
            a_form.form_directory,
            "repository",
            "mysql_drop_audit.sql",
        ]
        drop_file = os.path.join(repository_directory, *parts)
        if os.path.exists(create_file) and os.path.exists(drop_file):
            args = ["mysql", "--defaults-file=" + my_cnf_file, a_form.form_schema]
            with open(drop_file) as input_drop_file:
                proc = Popen(args, stdin=input_drop_file, stderr=PIPE, stdout=PIPE)
                output, error = proc.communicate()
                if proc.returncode == 0:
                    args = [
                        "mysql",
                        "--defaults-file=" + my_cnf_file,
                        a_form.form_schema,
                    ]
                    with open(create_file + ".5657a4829a73") as input_create_file:
                        proc = Popen(
                            args, stdin=input_create_file, stderr=PIPE, stdout=PIPE
                        )
                        output, error = proc.communicate()
                        if proc.returncode != 0:
                            print(
                                "Cannot create new triggers for schema {} with file {}. Error:{}-{}".format(
                                    a_form.form_schema,
                                    create_file,
                                    output.decode(),
                                    error.decode(),
                                )
                            )
                            exit(1)
                else:
                    print(
                        "Cannot drop old triggers for schema {} with file {}. Error:{}-{}".format(
                            a_form.form_schema,
                            drop_file + ".5657a4829a73",
                            output.decode(),
                            error.decode(),
                        )
                    )
                    exit(1)

            shutil.copyfile(create_file + ".5657a4829a73", create_file)
            shutil.copyfile(drop_file + ".5657a4829a73", drop_file)
            os.remove(create_file + ".5657a4829a73")
            os.remove(drop_file + ".5657a4829a73")

    session.commit()
