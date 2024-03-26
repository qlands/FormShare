"""Upgrade create.xml files to separate _geopoint

Revision ID: 7a31fe6e7d09
Revises: 0d5b7b290d86
Create Date: 2020-04-21 08:36:48.140455

"""

import os
import shutil
from pathlib import Path

from alembic import context
from lxml import etree
from pyramid.paster import get_appsettings, setup_logging

# revision identifiers, used by Alembic.
revision = "7a31fe6e7d09"
down_revision = "0d5b7b290d86"
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
    repository_directory = settings.get("repository.path", "")
    if repository_directory == "":
        print("Cannot find the repository path.")
        exit(1)
    parts = ["odk", "forms"]
    forms_directory = os.path.join(repository_directory, *parts)
    for path in Path(forms_directory).rglob("create.xml"):
        shutil.copyfile(str(path.absolute()), str(path.absolute()) + ".7a31fe6e7d09")
        parser = etree.XMLParser(remove_blank_text=True)
        tree_create = etree.parse(str(path.absolute()), parser)
        root_create = tree_create.getroot()
        main_table = root_create.find(".//table[@name='maintable']")
        if main_table is not None:
            longitude_field = main_table.find(".//field[@name='_longitude']")
            if longitude_field is None:
                fields = main_table.findall(".//field")
                if fields:
                    geopoint = None
                    for a_field in fields:
                        if a_field.get("name", "") == "_geopoint":
                            geopoint = a_field
                            break
                    if geopoint is not None:
                        longitude = etree.Element(
                            "field",
                            desc="GPS Point Longitude",
                            size="0",
                            decsize="0",
                            name="_longitude",
                            sensitive="true",
                            xmlcode="_longitude",
                            odktype="decimal",
                            type="double",
                            protection="exclude",
                        )
                        latitude = etree.Element(
                            "field",
                            desc="GPS Point Latitude",
                            size="0",
                            decsize="0",
                            name="_latitude",
                            sensitive="true",
                            xmlcode="_latitude",
                            odktype="decimal",
                            type="double",
                            protection="exclude",
                        )
                        elevation = etree.Element(
                            "field",
                            desc="GPS Point Elevation",
                            size="9",
                            decsize="3",
                            name="_elevation",
                            xmlcode="_elevation",
                            odktype="decimal",
                            type="decimal",
                        )
                        precision = etree.Element(
                            "field",
                            desc="GPS Point Precision",
                            size="9",
                            decsize="3",
                            name="_precision",
                            xmlcode="_precision",
                            odktype="decimal",
                            type="decimal",
                        )
                        geopoint.addnext(precision)
                        geopoint.addnext(elevation)
                        geopoint.addnext(latitude)
                        geopoint.addnext(longitude)

                        tree_create.write(
                            str(path.absolute()),
                            pretty_print=True,
                            xml_declaration=True,
                            encoding="utf-8",
                        )


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
    repository_directory = settings.get("repository.path", "")
    if repository_directory == "":
        print("Cannot find the respository path.")
        exit(1)
    parts = ["odk", "forms"]
    forms_directory = os.path.join(repository_directory, *parts)
    for path in Path(forms_directory).rglob("create.xml.7a31fe6e7d09"):
        shutil.copy(
            str(path.absolute()), str(path.absolute()).replace(".7a31fe6e7d09", "")
        )
        os.remove(str(path.absolute()))
