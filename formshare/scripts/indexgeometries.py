"""Indexes the locations of the submissions already in the dataset index,
once, after the upgrades that taught FormShare to draw traces and shapes and
then every location of a main table (processes/geometry.py, migration
f5c8a1e3b7d9).

    index_geometries [--project <project id>] [--form <form id>] <ini file>

For every form with a geotrace, a geoshape or more than one geopoint, each
submission's stored JSON gives its document a _geoshape and a _geotype, and
a _geolocation when no geopoint gave one, as a new submission gets them. A
document is updated in place. A submission whose JSON or document is missing
is counted and left.
"""

import argparse
import json
import logging
import os

from elasticsearch.exceptions import NotFoundError

from formshare.app import load_settings_from_ini
from sqlalchemy import or_

from formshare.models import Odkform, Submission, get_engine, get_session_factory
from formshare.processes.elasticsearch.repository_index import (
    create_connection,
    get_index_name,
)
from formshare.processes.geometry import add_location, parse_geoshape_variables


def main(raw_args=None):
    parser = argparse.ArgumentParser(
        description="Index the locations of the submissions already indexed"
    )
    parser.add_argument("--project", help="Only the forms of this project id")
    parser.add_argument("--form", help="Only the form with this id")
    parser.add_argument("ini_path", help="Path to ini file")
    args = parser.parse_args(raw_args)
    if not os.path.exists(args.ini_path):
        logging.error("Ini file does not exists")
        return 1

    settings = load_settings_from_ini(os.path.abspath(args.ini_path))
    connection = create_connection(settings)
    if connection is None:
        logging.error("Cannot connect to ElasticSearch")
        return 1
    index_name = get_index_name(settings)
    odk_dir = os.path.join(settings["repository.path"], "odk")
    engine = get_engine(settings)
    session = get_session_factory(engine)()
    counts = {"updated": 0, "nothing": 0, "missing": 0}
    try:
        # A form with one geopoint and nothing else is indexed as it always
        # was; any other location now gives its submissions a _geoshape.
        forms = session.query(
            Odkform.project_id,
            Odkform.form_id,
            Odkform.form_directory,
            Odkform.form_geoshape,
            Odkform.form_geopoint,
        ).filter(
            or_(
                Odkform.form_geoshape.isnot(None),
                Odkform.form_geopoint.like("%,%"),
            )
        )
        if args.project:
            forms = forms.filter(Odkform.project_id == args.project)
        if args.form:
            forms = forms.filter(Odkform.form_id == args.form)
        for a_form in forms.all():
            variables = parse_geoshape_variables(a_form.form_geoshape)
            points = (
                (a_form.form_geopoint or "").split(",") if a_form.form_geopoint else []
            )
            submissions = (
                session.query(Submission.submission_id)
                .filter(Submission.project_id == a_form.project_id)
                .filter(Submission.form_id == a_form.form_id)
                .filter(Submission.sameas.is_(None))
                .all()
            )
            for (submission_id,) in submissions:
                json_file = os.path.join(
                    odk_dir,
                    *[
                        "forms",
                        a_form.form_directory,
                        "submissions",
                        submission_id + ".json",
                    ]
                )
                try:
                    with open(json_file, encoding="utf-8") as a_file:
                        submission_data = json.load(a_file)
                except (OSError, ValueError):
                    counts["missing"] += 1
                    continue
                document = {}
                if submission_data.get("_geolocation"):
                    document["_geolocation"] = submission_data["_geolocation"]
                add_location(document, submission_data, variables, points)
                if "_geoshape" not in document:
                    counts["nothing"] += 1
                    continue
                try:
                    connection.update(index=index_name, id=submission_id, doc=document)
                    counts["updated"] += 1
                except NotFoundError:
                    counts["missing"] += 1
    finally:
        session.close()
        engine.dispose()
        connection.close()
    print(
        "Indexed the locations of {updated} submission(s). {nothing} had nothing "
        "beyond one geopoint to draw; {missing} had no JSON or no document.".format(
            **counts
        )
    )
    return 0
