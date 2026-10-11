"""Writing a repository table's audit triggers again (processes/
audit_triggers.py), without a server: telling a createaudittriggers that
still audits generated columns from one that leaves them out, and putting a
saved trigger back without its DEFINER.
"""

from formshare.processes.audit_triggers import names_generated, without_definer

# What a createaudittriggers from before rstools.md 29 wrote on a table with
# a trace: the geometry audited beside its answer, names unquoted.
BEFORE = (
    "IF IFnull(OLD.route,'NULL') <> IFNULL(NEW.route,'NULL') THEN INSERT INTO "
    "audit_log(audit_column,audit_oldvalue,audit_newvalue) VALUES "
    "('route',OLD.route,NEW.route); END IF; "
    "IF IFnull(OLD.route_geom,'NULL') <> IFNULL(NEW.route_geom,'NULL') THEN "
    "INSERT INTO audit_log(audit_column,audit_oldvalue,audit_newvalue) VALUES "
    "('route_geom',OLD.route_geom,NEW.route_geom); END IF;"
)
# What one since writes: names quoted, the geometry left out.
SINCE = (
    "IF IFnull(OLD.`route`,'NULL') <> IFNULL(NEW.`route`,'NULL') THEN INSERT "
    "INTO audit_log(audit_column,audit_oldvalue,audit_newvalue) VALUES "
    "('route',OLD.`route`,NEW.`route`); END IF;"
)


def test_a_tool_that_audits_a_generated_column_is_told_apart():
    assert names_generated(BEFORE, ["route_geom"]) == ["route_geom"]
    assert names_generated(SINCE, ["route_geom"]) == []
    # Quoted, as an identifier or as the column audit_log is told about.
    assert names_generated("NEW.`plot_geom`", ["plot_geom"]) == ["plot_geom"]
    assert names_generated("'plot_geom'", ["plot_geom", "route_geom"]) == ["plot_geom"]


def test_a_longer_name_is_not_the_generated_column():
    # A GeoJSON lookup generates geometry from geometry_json; a question may
    # be called route_geometry_note.
    assert names_generated("OLD.`geometry_json`", ["geometry"]) == []
    assert names_generated("NEW.route_geometry_note", ["route_geom"]) == []
    assert names_generated("OLD.`geometry`", ["geometry"]) == ["geometry"]


def test_a_trigger_comes_back_as_whoever_restores_it():
    statement = (
        "CREATE DEFINER=`root`@`%` TRIGGER `audit_1_update` AFTER UPDATE ON "
        "`maintable` FOR EACH ROW BEGIN SET @a = 1; END"
    )
    assert without_definer(statement) == (
        "CREATE TRIGGER `audit_1_update` AFTER UPDATE ON `maintable` FOR EACH "
        "ROW BEGIN SET @a = 1; END"
    )
    assert without_definer(
        "CREATE DEFINER=formshare@localhost TRIGGER t BEFORE INSERT ON x FOR "
        "EACH ROW SET @a = 1"
    ) == ("CREATE TRIGGER t BEFORE INSERT ON x FOR EACH ROW SET @a = 1")
    # Nothing to take out.
    assert without_definer(
        "CREATE TRIGGER t BEFORE INSERT ON x FOR EACH ROW SET @a = 1"
    ) == ("CREATE TRIGGER t BEFORE INSERT ON x FOR EACH ROW SET @a = 1")
