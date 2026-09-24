"""A file jxformtomysql cannot write, and whether the tool says so.

Since rstools.md 17.2 jxformtomysql ends with 38 when a file it was told to
write cannot be opened or is not written whole. An older tool ended with 0
and left the file out, so a step that makes a file unwritable first asks the
installed tool which of the two it is: the image CI runs may predate the code.

A directory where the file goes is what makes it unwritable. Opening it
fails with "Is a directory" whoever runs the tool, root included, which a
read-only directory would not stop.
"""

import json
import os
import shutil
from subprocess import Popen, PIPE

import openpyxl
from pyxform.xls2json import parse_file_to_json


def make_unwritable(path):
    """Puts a directory where the file ``path`` goes."""
    if os.path.isdir(path):
        return
    if os.path.exists(path):
        os.remove(path)
    os.makedirs(path)


def make_writable(path):
    """Takes the directory away again; the next run writes the file."""
    if os.path.isdir(path):
        os.rmdir(path)


def small_form(work):
    """The JSON (.srv) of the smallest form a check accepts, keyed by hid."""
    book = openpyxl.Workbook()
    survey = book.active
    survey.title = "survey"
    survey.append(["type", "name", "label"])
    survey.append(["text", "hid", "Household id"])
    survey.append(["integer", "members", "Members"])
    settings = book.create_sheet("settings")
    settings.append(["form_title", "form_id", "version"])
    settings.append(["Unwritable output", "unwritable_output", "1"])
    xlsx = os.path.join(work, "unwritable_output.xlsx")
    book.save(xlsx)
    srv = os.path.join(work, "unwritable_output.srv")
    with open(srv, "w", encoding="utf-8") as a_file:
        a_file.write(json.dumps(parse_file_to_json(xlsx, warnings=[]), indent=4))
    return srv


def tool_reports_unwritable_files(odktools_path, work):
    """True when the installed jxformtomysql ends with 38 for a file it could
    not write, False when it predates the code. Runs a check of the small
    form with a directory where its manifest goes."""
    probe = os.path.join(work, "exit38_probe")
    if os.path.exists(probe):
        shutil.rmtree(probe)
    os.makedirs(probe)
    try:
        srv = small_form(probe)
        make_unwritable(os.path.join(probe, "manifest.xml"))
        args = [
            os.path.join(odktools_path, "JXFormToMysql", "jxformtomysql"),
            "-j " + srv,
            "-C " + os.path.join(probe, "create.xml"),
            "-I " + os.path.join(probe, "insert.xml"),
            "-f " + os.path.join(probe, "manifest.xml"),
            "-t maintable",
            "-v hid",
            "-e " + os.path.join(probe, "tmp"),
            "-o m",
            "-K",
        ]
        p = Popen(args, stdout=PIPE, stderr=PIPE, cwd=probe)
        p.communicate()
        return p.returncode == 38
    finally:
        shutil.rmtree(probe, ignore_errors=True)
