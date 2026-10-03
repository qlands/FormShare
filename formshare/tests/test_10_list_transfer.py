"""The published-list document and the rules of its import, without a server.

processes/db/list_transfer.py reads the project through a handful of
functions of processes/db/case_management.py; here they are replaced by a
project held in memory, so every rule can be shown to refuse what it should
and to write nothing when it does.
"""

import datetime
import json
import unittest

import yaml

from formshare.processes.db import list_transfer as lt


class _Request:
    def translate(self, text):
        return text


class _Project:
    """A project with two forms, one with a repository, and one list."""

    def __init__(self):
        self.forms = {
            "reg": {"form_id": "reg", "form_schema": "FS_reg"},
            "draft": {"form_id": "draft", "form_schema": None},
        }
        self.tables = {"reg": ["maintable", "members"], "draft": ["maintable"]}
        self.columns = {
            ("reg", "maintable"): ["farmer_id", "farmer_name", "county", "village"],
            ("reg", "members"): ["member_name", "parent_rowuuid"],
        }
        self.properties = {
            ("reg", "maintable"): [
                {"property_name": "stage", "property_type": "string"}
            ]
        }
        self.lists = [
            {
                "list_id": "old",
                "list_filename": "old.csv",
                "source_project": "P",
                "source_form": "reg",
                "source_table": "maintable",
            }
        ]
        self.created_properties = []
        self.added_lists = []
        self.columns_set = {}
        self.deleted = []
        self.fail_columns_of = None

    def install(self, test):
        replaced = {
            "get_form_data": lambda r, p, f: self.forms.get(f),
            "get_form_data_tables": lambda r, p, f: [
                {"table_name": t} for t in self.tables.get(f, [])
            ],
            "get_table_columns": lambda r, p, f, t: [
                {"field_name": c} for c in self.columns.get((f, t), [])
            ],
            "get_table_properties": lambda r, p, f, t: list(
                self.properties.get((f, t), [])
            ),
            "get_project_published_lists": lambda r, p: list(self.lists),
            "get_list_source_tables": lambda r, p: {"reg": ["maintable"]},
            "add_table_property": self.add_table_property,
            "add_published_list": self.add_published_list,
            "set_list_columns": self.set_list_columns,
            "delete_published_list": self.delete_published_list,
        }
        for name, function in replaced.items():
            original = getattr(lt, name)
            setattr(lt, name, function)
            test.addCleanup(setattr, lt, name, original)

    def add_table_property(self, r, p, f, t, name, ptype, default, desc, user):
        self.created_properties.append((f, t, name, ptype, default, desc, user))
        return True, ""

    def add_published_list(self, r, p, list_data):
        self.added_lists.append(dict(list_data))
        return True, ""

    def set_list_columns(self, r, p, list_id, columns):
        if list_id == self.fail_columns_of:
            return False, "the database said no"
        self.columns_set[list_id] = list(columns)
        return True, ""

    def delete_published_list(self, r, p, list_id):
        self.deleted.append(list_id)
        return True, ""


def _document(lists=None, properties=None):
    return {
        "document": lt.DOCUMENT,
        "version": lt.VERSION,
        "properties": properties or [],
        "lists": lists,
    }


def _farmers(**changes):
    a_list = {
        "code": "farmers",
        "file_name": "farmers.csv",
        "form_id": "reg",
        "table": "maintable",
        "label_column": "farmer_name",
        "key_column": None,
        "rows": "active",
        "columns": [
            {"column": "county", "served_as": "region"},
            {"property": "stage"},
            {"property": "visits"},
        ],
    }
    a_list.update(changes)
    return a_list


VISITS = {
    "form_id": "reg",
    "table": "maintable",
    "name": "visits",
    "type": "integer",
    "default": "0",
    "description": "Visits so far",
}


class LoadDocument(unittest.TestCase):
    def test_json_and_yaml_read_alike(self):
        document = _document([_farmers()], [VISITS])
        for text in (
            lt.dump_document(document, "json"),
            lt.dump_document(document, "yaml"),
        ):
            loaded, error = lt.load_document(text.encode("utf-8"))
            self.assertEqual(error, "")
            self.assertEqual(loaded, document)

    def test_yaml_keeps_text_that_looks_like_something_else(self):
        # A default of "yes", "0012" or a date stays text through YAML: the
        # dump quotes what YAML would otherwise read as another type.
        properties = [
            dict(VISITS, name="answer", type="string", default="yes"),
            dict(VISITS, name="code", type="string", default="0012"),
            dict(VISITS, name="since", type="date", default="2026-03-01"),
        ]
        loaded, _ = lt.load_document(
            lt.dump_document(_document([_farmers()], properties), "yaml")
        )
        self.assertEqual(
            [p["default"] for p in loaded["properties"]], ["yes", "0012", "2026-03-01"]
        )

    def test_what_is_not_a_document(self):
        self.assertEqual(
            lt.load_document(b"\xff\xfe\x00")[1], "The file is not UTF-8 text"
        )
        self.assertTrue(
            lt.load_document(b"key: [unclosed")[1].startswith(
                "The file is neither JSON nor YAML"
            )
        )
        self.assertEqual(
            lt.load_document(b'{"lists": []}')[1],
            "The file is not a list export of FormShare",
        )
        self.assertEqual(
            lt.load_document(b"just text")[1],
            "The file is not a list export of FormShare",
        )
        later = json.dumps({"document": lt.DOCUMENT, "version": 2, "lists": []})
        self.assertEqual(
            lt.load_document(later)[1],
            "The file is version 2 of the export, and this FormShare reads version 1",
        )


class TextOfAScalar(unittest.TestCase):
    def test_scalars(self):
        self.assertEqual(lt._text(datetime.date(2026, 3, 1)), ("2026-03-01", True))
        self.assertEqual(
            lt._text(datetime.datetime(2026, 3, 1, 8, 30)),
            ("2026-03-01 08:30:00", True),
        )
        self.assertEqual(lt._text(12), ("12", True))
        self.assertEqual(lt._text(None), (None, True))
        self.assertEqual(lt._text(True), (None, False))
        self.assertEqual(lt._text({"a": 1}), (None, False))


class ImportLists(unittest.TestCase):
    def setUp(self):
        self.project = _Project()
        self.project.install(self)
        self.request = _Request()

    def run_import(self, document):
        return lt.import_lists(self.request, "P", document, "owner")

    def assertNothingWritten(self):
        self.assertEqual(self.project.created_properties, [])
        self.assertEqual(self.project.added_lists, [])

    def test_a_good_document(self):
        members = {
            "code": "members",
            "file_name": "members.csv",
            "form_id": "reg",
            "table": "members",
            "label_column": "member_name",
            "rows": "inactive",
            "columns": [{"column": "parent_rowuuid", "served_as": "farmer"}],
        }
        counties = {
            "code": "counties",
            "file_name": "counties.csv",
            "form_id": "reg",
            "table": "maintable",
            "label_column": "county",
            "key_column": "county",
            "columns": [],
        }
        stage = dict(VISITS, name="stage", type="string", default="registered")
        done, errors, warnings = self.run_import(
            _document([_farmers(), members, counties], [stage, VISITS])
        )
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        # stage exists with the same type, so it is kept; visits is created.
        self.assertEqual(done["properties"], ["visits"])
        self.assertEqual(done["kept"], ["stage"])
        self.assertEqual(
            self.project.created_properties,
            [("reg", "maintable", "visits", "integer", "0", "Visits so far", "owner")],
        )
        self.assertEqual(done["lists"], ["farmers", "members", "counties"])
        farmers, members_list, counties_list = self.project.added_lists
        # The source is the importing project's form, whatever exported it.
        self.assertEqual(farmers["source_project"], "P")
        self.assertEqual(farmers["source_form"], "reg")
        self.assertEqual(farmers["list_format"], "csv")
        self.assertEqual(farmers["list_active"], 1)
        self.assertIsNone(farmers["list_key_column"])
        self.assertEqual(members_list["list_active"], 0)
        self.assertEqual(counties_list["list_key_column"], "county")
        self.assertEqual(
            self.project.columns_set["farmers"],
            [
                ("county", "region", "table"),
                ("stage", None, "property"),
                ("visits", None, "property"),
            ],
        )
        self.assertEqual(
            self.project.columns_set["members"],
            [("parent_rowuuid", "farmer", "table")],
        )

    def test_an_unknown_key_is_reported_and_left(self):
        done, errors, warnings = self.run_import(
            _document([_farmers(colour="green")], [VISITS])
        )
        self.assertEqual(errors, [])
        self.assertEqual(warnings, ['List "farmers": not imported: colour'])
        self.assertEqual(done["lists"], ["farmers"])

    def test_a_filter_is_compiled_against_the_importing_table(self):
        # It may read a property the same document is about to create.
        rules = {
            "condition": "AND",
            "rules": [
                {"id": "t.county", "operator": "equal", "value": "kitui"},
                {"id": "p.visits", "operator": "greater", "value": 0},
            ],
        }
        done, errors, warnings = self.run_import(
            _document([_farmers(filter=rules)], [VISITS])
        )
        self.assertEqual(errors, [])
        added = self.project.added_lists[0]
        self.assertEqual(json.loads(added["filter_rules"]), rules)
        self.assertIn("HEX({t}`county`)", added["filter_sql"])
        self.assertIn("{p}`visits`", added["filter_sql"])

    def test_no_filter_stores_none(self):
        self.run_import(_document([_farmers(filter={})], [VISITS]))
        added = self.project.added_lists[0]
        self.assertIsNone(added["filter_rules"])
        self.assertIsNone(added["filter_sql"])

    def test_a_filter_the_table_cannot_run_is_refused(self):
        self.assertRefused(
            _document(
                [
                    _farmers(
                        filter={
                            "condition": "AND",
                            "rules": [
                                {"id": "t.nope", "operator": "equal", "value": "x"}
                            ],
                        }
                    )
                ],
                [VISITS],
            ),
            "its filter: The list's table has no field t.nope",
        )
        self.assertRefused(
            _document([_farmers(filter="county = 1")], [VISITS]),
            "its filter is not a rule set",
        )

    def assertRefused(self, document, expected):
        done, errors, warnings = self.run_import(document)
        self.assertTrue(
            any(expected in an_error for an_error in errors),
            "{!r} not in {!r}".format(expected, errors),
        )
        self.assertNothingWritten()
        self.assertEqual(done, {"lists": [], "properties": [], "kept": []})

    def test_the_form_must_exist(self):
        self.assertRefused(
            _document([_farmers(form_id="ghost")], [VISITS]),
            'The form "ghost" does not exist in this project',
        )

    def test_the_form_needs_its_repository(self):
        self.assertRefused(
            _document([_farmers(form_id="draft", columns=[])]),
            'The form "draft" has no repository yet',
        )

    def test_the_table_must_be_a_data_table_of_the_form(self):
        self.assertRefused(
            _document([_farmers(table="lkpcounty", columns=[])]),
            'The form "reg" has no table "lkpcounty"',
        )

    def test_every_column_must_exist(self):
        self.assertRefused(
            _document([_farmers(label_column="nope", columns=[])]),
            'the table has no column "nope" to label with',
        )
        self.assertRefused(
            _document([_farmers(key_column="nope", columns=[])]),
            'the table has no column "nope" to key with',
        )
        self.assertRefused(
            _document([_farmers(columns=[{"column": "nope"}])]),
            'the table has no column "nope"',
        )

    def test_a_served_property_must_exist_or_be_defined(self):
        self.assertRefused(
            _document([_farmers()]),
            'it serves the property "visits", which the table does not have '
            "and the file does not define",
        )

    def test_a_property_must_agree_with_the_table(self):
        self.assertRefused(
            _document(
                [_farmers()], [VISITS, dict(VISITS, name="stage", type="integer")]
            ),
            "the table has it already, as string",
        )

    def test_a_property_must_be_valid(self):
        self.assertRefused(
            _document([_farmers()], [dict(VISITS, name="Visits")]),
            "a property name is lower case",
        )
        self.assertRefused(
            _document([_farmers()], [VISITS, dict(VISITS, name="village")]),
            "the table has a column of that name",
        )
        self.assertRefused(
            _document([_farmers()], [dict(VISITS, type="colour")]),
            "its type must be one of",
        )
        self.assertRefused(
            _document([_farmers()], [dict(VISITS, default=True)]),
            "write its default and its description in quotes",
        )
        refused = self.run_import(_document([_farmers()], [dict(VISITS, default="x")]))
        self.assertTrue(refused[1])
        self.assertNothingWritten()

    def test_a_property_defined_twice_must_agree(self):
        self.assertRefused(
            _document([_farmers()], [VISITS, dict(VISITS, default="1")]),
            "the file defines it twice, differently",
        )

    def test_a_property_belongs_on_a_table_a_list_draws_from(self):
        self.assertRefused(
            _document(
                [_farmers(columns=[])],
                [dict(VISITS, table="members", name="seen")],
            ),
            "no list draws from its table",
        )

    def test_codes_and_file_names_are_unique(self):
        self.assertRefused(
            _document([_farmers(code="old", columns=[])]),
            "its code is in use, in the project or earlier in the file",
        )
        self.assertRefused(
            _document([_farmers(file_name="old.csv", columns=[])]),
            'its file "old.csv" is in use',
        )
        twice = _farmers(columns=[])
        self.assertRefused(
            _document([twice, dict(twice, file_name="other.csv")]),
            "its code is in use, in the project or earlier in the file",
        )

    def test_names_the_wizard_would_refuse(self):
        self.assertRefused(
            _document([_farmers(code="add", columns=[])]),
            "its code is lower case letters",
        )
        self.assertRefused(
            _document([_farmers(file_name="farmers.geojson", columns=[])]),
            "end in .csv",
        )
        self.assertRefused(
            _document([_farmers(rows="all", columns=[])]),
            "its rows are active or inactive",
        )

    def test_served_names(self):
        self.assertRefused(
            _document([_farmers(columns=[{"column": "county", "served_as": "label"}])]),
            'two served columns are called "label"',
        )
        self.assertRefused(
            _document(
                [
                    _farmers(
                        columns=[
                            {"column": "county", "served_as": "place"},
                            {"column": "village", "served_as": "place"},
                        ]
                    )
                ]
            ),
            'two served columns are called "place"',
        )
        self.assertRefused(
            _document(
                [_farmers(columns=[{"column": "county", "served_as": "the place"}])]
            ),
            '"the place" cannot be a served name',
        )
        self.assertRefused(
            _document([_farmers(columns=[{"column": "county", "property": "stage"}])]),
            "its column 1 names one column or one property",
        )

    def test_every_problem_is_reported_at_once(self):
        done, errors, warnings = self.run_import(
            _document(
                [_farmers(form_id="ghost"), _farmers(code="b", label_column="nope")],
                [dict(VISITS, type="colour")],
            )
        )
        self.assertEqual(len(errors), 3, errors)
        self.assertNothingWritten()

    def test_a_failed_write_stops_and_says_how_far_it_got(self):
        second = _farmers(code="second", file_name="second.csv", columns=[])
        self.project.fail_columns_of = "second"
        done, errors, warnings = self.run_import(
            _document([_farmers(), second], [VISITS])
        )
        self.assertEqual(done["properties"], ["visits"])
        self.assertEqual(done["lists"], ["farmers"])
        self.assertEqual(errors, ['List "second": the database said no'])
        # The list without its columns is taken out again.
        self.assertEqual(self.project.deleted, ["second"])


class ExportDocument(unittest.TestCase):
    def test_a_list_and_its_tables_properties(self):
        project = _Project()
        project.install(self)
        project.lists = [
            {
                "list_id": "farmers",
                "list_filename": "farmers.csv",
                "source_project": "P",
                "source_form": "reg",
                "source_table": "maintable",
                "label_column": "farmer_name",
                "list_key_column": None,
                "list_active": 1,
                "list_createdate": datetime.datetime(2026, 3, 1, 9, 0),
                "filter_rules": '{"condition": "AND", "rules": []}',
            },
            {
                "list_id": "counties",
                "list_filename": "counties.csv",
                "source_project": "P",
                "source_form": "reg",
                "source_table": "maintable",
                "label_column": "county",
                "list_key_column": "county",
                "list_active": 0,
                "list_createdate": datetime.datetime(2026, 3, 1, 10, 0),
                "filter_rules": "not json",
            },
        ]
        project.properties[("reg", "maintable")] = [
            {
                "property_name": "stage",
                "property_type": "string",
                "property_default": "registered",
                "property_desc": None,
            }
        ]
        columns = {
            "farmers": [
                {
                    "column_name": "county",
                    "column_as": "region",
                    "column_source": "table",
                },
                {
                    "column_name": "stage",
                    "column_as": None,
                    "column_source": "property",
                },
            ],
            "counties": [],
        }
        original = lt.get_list_columns
        lt.get_list_columns = lambda r, p, list_id: columns[list_id]
        self.addCleanup(setattr, lt, "get_list_columns", original)

        document = lt.list_document(_Request(), "P")
        self.assertEqual(document["document"], lt.DOCUMENT)
        self.assertEqual(
            [a["code"] for a in document["lists"]], ["farmers", "counties"]
        )
        self.assertEqual(
            document["lists"][0]["columns"],
            [{"column": "county", "served_as": "region"}, {"property": "stage"}],
        )
        self.assertEqual(document["lists"][1]["rows"], "inactive")
        # A stored filter travels as the rule set it is; one that does not
        # read as one is left out.
        self.assertEqual(
            document["lists"][0]["filter"], {"condition": "AND", "rules": []}
        )
        self.assertNotIn("filter", document["lists"][1])
        self.assertEqual(document["lists"][1]["key_column"], "county")
        # Two lists from one table: its properties once.
        self.assertEqual(
            document["properties"],
            [
                {
                    "form_id": "reg",
                    "table": "maintable",
                    "name": "stage",
                    "type": "string",
                    "default": "registered",
                    "description": None,
                }
            ],
        )
        only = lt.list_document(_Request(), "P", ["counties"])
        self.assertEqual([a["code"] for a in only["lists"]], ["counties"])
        # What the export writes, the import reads back unchanged.
        self.assertEqual(yaml.safe_load(lt.dump_document(document, "yaml")), document)
