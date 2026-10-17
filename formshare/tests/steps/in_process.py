"""A repository built in the test process, as the worker builds it: what the
steps that need one and no Celery share (testing_data_handover,
per_assistant_lists)."""

import datetime
import os
import uuid
from subprocess import Popen, PIPE

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


def form_row(config, project_id, form_id):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        row = engine.execute(
            "SELECT form_directory, form_schema, form_blocked, form_jsonfile, "
            "form_createxmlfile, form_hexcolor FROM odkform "
            "WHERE project_id = %s AND form_id = %s",
            (project_id, form_id),
        ).fetchone()
        return dict(row._mapping)
    finally:
        engine.dispose()


def add_task(config, project_id, form_id, product_id, user):
    """The product row a task reports its progress to."""
    task_id = str(uuid.uuid4())
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    try:
        engine.execute(
            "INSERT INTO product (project_id, form_id, product_id, celery_taskid, "
            "datetime_added, created_by, process_only, output_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, 1, %s)",
            (
                project_id,
                form_id,
                product_id,
                task_id,
                datetime.datetime.now(),
                user,
                task_id[-12:],
            ),
        )
    finally:
        engine.dispose()
    return task_id


def build_in_process(
    test_object,
    project_id,
    project_code,
    form_id,
    primary_key,
    files,
    assigns_cases=True,
):
    """Builds a form's repository in this process, discarding its testing
    data, as create_mysql_repository does in the worker. files are the CSV
    and GeoJSON files the form selects from. assigns_cases=False leaves out
    _assigned_to, as in a repository built before stage 8."""
    from formshare.products.repository.celery_task import (
        internal_create_mysql_repository,
    )

    config = test_object.server_config
    row = form_row(config, project_id, form_id)
    work = os.path.join(test_object.working_dir, "build_" + uuid.uuid4().hex[:8])
    os.makedirs(work)
    output = {
        name: os.path.join(work, name)
        for name in (
            "create.sql",
            "create.xml",
            "insert.sql",
            "insert.xml",
            "drop.sql",
            "metadata.sql",
            "manifest.xml",
            "iso639.sql",
        )
    }
    args = [
        os.path.join(config["odktools.path"], "JXFormToMysql", "jxformtomysql"),
        "-j " + row["form_jsonfile"],
        "-t maintable",
        "-v " + primary_key,
        "-c " + output["create.sql"],
        "-C " + output["create.xml"],
        "-i " + output["insert.sql"],
        "-D " + output["drop.sql"],
        "-I " + output["insert.xml"],
        "-m " + output["metadata.sql"],
        "-f " + output["manifest.xml"],
        "-T " + output["iso639.sql"],
        "-e " + os.path.join(work, "temp"),
        "-L",
        "-o m",
    ]
    if assigns_cases:
        args.append("-a")
    args = args + files
    p = Popen(args, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    assert p.returncode == 0, stdout + stderr

    here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
    internal_create_mysql_repository(
        config,
        test_object.randonLogin,
        project_id,
        project_code,
        form_id,
        os.path.join(config["repository.path"], "odk"),
        row["form_directory"],
        "FS_" + str(uuid.uuid4()).replace("-", "_"),
        primary_key,
        os.path.join(here, "mysql.cnf"),
        output["create.sql"],
        output["insert.sql"],
        output["create.xml"],
        output["insert.xml"],
        "",
        "en",
        True,
        [],
        add_task(config, project_id, form_id, "repository", test_object.randonLogin),
    )
