import datetime
import logging
import uuid

import dateutil.parser
from sqlalchemy.exc import IntegrityError

from formshare.models import (
    Project,
    Userproject,
    map_to_schema,
    map_from_schema,
    Odkform,
    ProjectFile,
    CaseLookUp,
)
from formshare.processes.db.form import get_by_details, get_form_data
from formshare.processes.elasticsearch.repository_index import (
    get_dataset_stats_for_project,
)

__all__ = [
    "get_project_id_from_name",
    "get_user_projects",
    "get_active_project",
    "add_project",
    "modify_project",
    "delete_project",
    "is_collaborator",
    "add_file_to_project",
    "get_project_files",
    "remove_file_from_project",
    "get_project_code_from_id",
    "get_project_details",
    "set_project_as_active",
    "get_project_owner",
    "get_project_access_type",
    "get_owned_project",
    "get_number_of_case_creators",
    "get_number_of_case_creators_with_repository",
    "get_case_form",
    "get_case_schema",
    "project_has_case_lookup_table",
    "invalid_aliases",
]

log = logging.getLogger("formshare")

invalid_aliases = [
    "ACCESSIBLE",
    "ACCOUNT",
    "ACTION",
    "ACTIVE",
    "ADD",
    "ADMIN",
    "AFTER",
    "AGAINST",
    "AGGREGATE",
    "ALGORITHM",
    "ALL",
    "ALTER",
    "ALWAYS",
    "ANALYSE",
    "ANALYZE",
    "AND",
    "ANY",
    "AS",
    "ASC",
    "ASCII",
    "ASENSITIVE",
    "AT",
    "AUTOEXTEND_SIZE",
    "AUTO_INCREMENT",
    "AVG",
    "AVG_ROW_LENGTH",
    "BACKUP",
    "BEFORE",
    "BEGIN",
    "BETWEEN",
    "BIGINT",
    "BINARY",
    "BINLOG",
    "BIT",
    "BLOB",
    "BLOCK",
    "BOOL",
    "BOOLEAN",
    "BOTH",
    "BTREE",
    "BUCKETS",
    "BY",
    "BYTE",
    "CACHE",
    "CALL",
    "CASCADE",
    "CASCADED",
    "CASE",
    "CATALOG_NAME",
    "CHAIN",
    "CHANGE",
    "CHANGED",
    "CHANNEL",
    "CHAR",
    "CHARACTER",
    "CHARSET",
    "CHECK",
    "CHECKSUM",
    "CIPHER",
    "CLASS_ORIGIN",
    "CLIENT",
    "CLONE",
    "CLOSE",
    "COALESCE",
    "CODE",
    "COLLATE",
    "COLLATION",
    "COLUMN",
    "COLUMNS",
    "COLUMN_FORMAT",
    "COLUMN_NAME",
    "COMMENT",
    "COMMIT",
    "COMMITTED",
    "COMPACT",
    "COMPLETION",
    "COMPONENT",
    "COMPRESSED",
    "COMPRESSION",
    "CONCURRENT",
    "CONDITION",
    "CONNECTION",
    "CONSISTENT",
    "CONSTRAINT",
    "CONSTRAINT_CATALOG",
    "CONSTRAINT_NAME",
    "CONSTRAINT_SCHEMA",
    "CONTAINS",
    "CONTEXT",
    "CONTINUE",
    "CONVERT",
    "CPU",
    "CREATE",
    "CROSS",
    "CUBE",
    "CUME_DIST",
    "CURRENT",
    "CURRENT_DATE",
    "CURRENT_TIME",
    "CURRENT_TIMESTAMP",
    "CURRENT_USER",
    "CURSOR",
    "CURSOR_NAME",
    "DATA",
    "DATABASE",
    "DATABASES",
    "DATAFILE",
    "DATE",
    "DATETIME",
    "DAY",
    "DAY_HOUR",
    "DAY_MICROSECOND",
    "DAY_MINUTE",
    "DAY_SECOND",
    "DEALLOCATE",
    "DEC",
    "DECIMAL",
    "DECLARE",
    "DEFAULT",
    "DEFAULT_AUTH",
    "DEFINER",
    "DEFINITION",
    "DELAYED",
    "DELAY_KEY_WRITE",
    "DELETE",
    "DENSE_RANK",
    "DESC",
    "DESCRIBE",
    "DESCRIPTION",
    "DES_KEY_FILE",
    "DETERMINISTIC",
    "DIAGNOSTICS",
    "DIRECTORY",
    "DISABLE",
    "DISCARD",
    "DISK",
    "DISTINCT",
    "DISTINCTROW",
    "DIV",
    "DO",
    "DOUBLE",
    "DROP",
    "DUAL",
    "DUMPFILE",
    "DUPLICATE",
    "DYNAMIC",
    "EACH",
    "ELSE",
    "ELSEIF",
    "EMPTY",
    "ENABLE",
    "ENCLOSED",
    "ENCRYPTION",
    "END",
    "ENDS",
    "ENFORCED",
    "ENGINE",
    "ENGINES",
    "ENUM",
    "ERROR",
    "ERRORS",
    "ESCAPE",
    "ESCAPED",
    "EVENT",
    "EVENTS",
    "EVERY",
    "EXCEPT",
    "EXCHANGE",
    "EXCLUDE",
    "EXECUTE",
    "EXISTS",
    "EXIT",
    "EXPANSION",
    "EXPIRE",
    "EXPLAIN",
    "EXPORT",
    "EXTENDED",
    "EXTENT_SIZE",
    "FALSE",
    "FAST",
    "FAULTS",
    "FETCH",
    "FIELDS",
    "FILE",
    "FILE_BLOCK_SIZE",
    "FILTER",
    "FIRST",
    "FIRST_VALUE",
    "FIXED",
    "FLOAT",
    "FLOAT4",
    "FLOAT8",
    "FLUSH",
    "FOLLOWING",
    "FOLLOWS",
    "FOR",
    "FORCE",
    "FOREIGN",
    "FORMAT",
    "FOUND",
    "FROM",
    "FULL",
    "FULLTEXT",
    "FUNCTION",
    "GENERAL",
    "GENERATED",
    "GEOMCOLLECTION",
    "GEOMETRY",
    "GEOMETRYCOLLECTION",
    "GET",
    "GET_FORMAT",
    "GET_MASTER_PUBLIC_KEY",
    "GLOBAL",
    "GRANT",
    "GRANTS",
    "GROUP",
    "GROUPING",
    "GROUPS",
    "GROUP_REPLICATION",
    "HANDLER",
    "HASH",
    "HAVING",
    "HELP",
    "HIGH_PRIORITY",
    "HISTOGRAM",
    "HISTORY",
    "HOST",
    "HOSTS",
    "HOUR",
    "HOUR_MICROSECOND",
    "HOUR_MINUTE",
    "HOUR_SECOND",
    "IDENTIFIED",
    "IF",
    "IGNORE",
    "IGNORE_SERVER_IDS",
    "IMPORT",
    "IN",
    "INACTIVE",
    "INDEX",
    "INDEXES",
    "INFILE",
    "INITIAL_SIZE",
    "INNER",
    "INOUT",
    "INSENSITIVE",
    "INSERT",
    "INSERT_METHOD",
    "INSTALL",
    "INSTANCE",
    "INT",
    "INT1",
    "INT2",
    "INT3",
    "INT4",
    "INT8",
    "INTEGER",
    "INTERVAL",
    "INTO",
    "INVISIBLE",
    "INVOKER",
    "IO",
    "IO_AFTER_GTIDS",
    "IO_BEFORE_GTIDS",
    "IO_THREAD",
    "IPC",
    "IS",
    "ISOLATION",
    "ISSUER",
    "ITERATE",
    "JOIN",
    "JSON",
    "JSON_TABLE",
    "KEY",
    "KEYS",
    "KEY_BLOCK_SIZE",
    "KILL",
    "LAG",
    "LAG ",
    "LANGUAGE",
    "LAST",
    "LAST_VALUE",
    "LATERAL",
    "LEAD",
    "LEADING",
    "LEAVE",
    "LEAVES",
    "LEFT",
    "LESS",
    "LEVEL",
    "LIKE",
    "LIMIT",
    "LINEAR",
    "LINES",
    "LINESTRING",
    "LIST",
    "LOAD",
    "LOCAL",
    "LOCALTIME",
    "LOCALTIMESTAMP",
    "LOCK",
    "LOCKED",
    "LOCKS",
    "LOGFILE",
    "LOGS",
    "LONG",
    "LONGBLOB ",
    "LONGTEXT",
    "LOOP",
    "LOW_PRIORITY",
    "MASTER",
    "MASTER_AUTO_POSITION",
    "MASTER_BIND",
    "MASTER_CONNECT_RETRY",
    "MASTER_DELAY",
    "MASTER_HEARTBEAT_PERIOD",
    "MASTER_HOST",
    "MASTER_LOG_FILE",
    "MASTER_LOG_POS",
    "MASTER_PASSWORD",
    "MASTER_PORT",
    "MASTER_PUBLIC_KEY_PATH",
    "MASTER_RETRY_COUNT",
    "MASTER_SERVER_ID",
    "MASTER_SSL",
    "MASTER_SSL_CA",
    "MASTER_SSL_CAPATH",
    "MASTER_SSL_CERT",
    "MASTER_SSL_CIPHER",
    "MASTER_SSL_CRL",
    "MASTER_SSL_CRLPATH",
    "MASTER_SSL_KEY",
    "MASTER_SSL_VERIFY_SERVER_CERT",
    "MASTER_TLS_VERSION",
    "MASTER_USER",
    "MATCH",
    "MAXVALUE",
    "MAX_CONNECTIONS_PER_HOUR",
    "MAX_QUERIES_PER_HOUR",
    "MAX_ROWS",
    "MAX_SIZE",
    "MAX_UPDATES_PER_HOUR",
    "MAX_USER_CONNECTIONS",
    "MEDIUM",
    "MEDIUMBLOB",
    "MEDIUMINT",
    "MEDIUMTEXT",
    "MEMORY",
    "MERGE",
    "MESSAGE_TEXT",
    "MICROSECOND",
    "MIDDLEINT",
    "MIGRATE",
    "MINUTE",
    "MINUTE_MICROSECOND",
    "MINUTE_SECOND",
    "MIN_ROWS",
    "MOD",
    "MODE",
    "MODIFIES",
    "MODIFY",
    "MONTH",
    "MULTILINESTRING",
    "MULTIPOINT",
    "MULTIPOLYGON",
    "MUTEX",
    "MYSQL_ERRNO",
    "NAME",
    "NAMES",
    "NATIONAL",
    "NATURAL",
    "NCHAR",
    "NDB",
    "NDBCLUSTER",
    "NESTED",
    "NETWORK_NAMESPACE",
    "NEVER",
    "NEW",
    "NEXT",
    "NO",
    "NODEGROUP",
    "NONE",
    "NOT",
    "NOWAIT",
    "NO_WAIT",
    "NO_WRITE_TO_BINLOG",
    "NTH_VALUE",
    "NTILE",
    "NULL",
    "NULLS",
    "NUMBER",
    "NUMERIC",
    "NVARCHAR",
    "OF",
    "OFFSET",
    "OJ",
    "OLD",
    "ON",
    "ONE",
    "ONLY",
    "OPEN",
    "OPTIMIZE",
    "OPTIMIZER_COSTS",
    "OPTION",
    "OPTIONAL",
    "OPTIONALLY",
    "OPTIONS",
    "OR",
    "ORDER",
    "ORDINALITY",
    "ORGANIZATION",
    "OTHERS",
    "OUT",
    "OUTER",
    "OUTFILE",
    "OVER",
    "OWNER",
    "PACK_KEYS",
    "PAGE",
    "PARSER",
    "PARSE_GCOL_EXPR",
    "PARTIAL",
    "PARTITION",
    "PARTITIONING",
    "PARTITIONS",
    "PASSWORD",
    "PATH",
    "PERCENT_RANK",
    "PERSIST",
    "PERSIST_ONLY",
    "PHASE",
    "PLUGIN",
    "PLUGINS",
    "PLUGIN_DIR",
    "POINT",
    "POLYGON",
    "PORT",
    "PRECEDES",
    "PRECEDING",
    "PRECISION",
    "PREPARE",
    "PRESERVE",
    "PREV",
    "PRIMARY",
    "PRIVILEGES",
    "PROCEDURE",
    "PROCESS",
    "PROCESSLIST",
    "PROFILE",
    "PROFILES",
    "PROXY",
    "PURGE",
    "QUARTER",
    "QUERY",
    "QUICK",
    "RANGE",
    "RANK",
    "READ",
    "READS",
    "READ_ONLY",
    "READ_WRITE",
    "REAL",
    "REBUILD",
    "RECOVER",
    "RECURSIVE",
    "REDOFILE",
    "REDO_BUFFER_SIZE",
    "REDUNDANT",
    "REFERENCE",
    "REFERENCES",
    "REGEXP",
    "RELAY",
    "RELAYLOG",
    "RELAY_LOG_FILE",
    "RELAY_LOG_POS",
    "RELAY_THREAD",
    "RELEASE",
    "RELOAD",
    "REMOTE",
    "REMOVE",
    "RENAME",
    "REORGANIZE",
    "REPAIR",
    "REPEAT",
    "REPEATABLE",
    "REPLACE",
    "REPLICATE_DO_DB",
    "REPLICATE_DO_TABLE",
    "REPLICATE_IGNORE_DB",
    "REPLICATE_IGNORE_TABLE",
    "REPLICATE_REWRITE_DB",
    "REPLICATE_WILD_DO_TABLE",
    "REPLICATE_WILD_IGNORE_TABLE",
    "REPLICATION",
    "REQUIRE",
    "RESET",
    "RESIGNAL",
    "RESOURCE",
    "RESPECT",
    "RESTART",
    "RESTORE",
    "RESTRICT",
    "RESUME",
    "RETAIN",
    "RETURN",
    "RETURNED_SQLSTATE",
    "RETURNS",
    "REUSE",
    "REVERSE",
    "REVOKE",
    "RIGHT",
    "RLIKE",
    "ROLE",
    "ROLLBACK",
    "ROLLUP",
    "ROTATE",
    "ROUTINE",
    "ROW",
    "ROWS",
    "ROW_COUNT",
    "ROW_FORMAT",
    "ROW_NUMBER",
    "RTREE",
    "SAVEPOINT",
    "SCHEDULE",
    "SCHEMA",
    "SCHEMAS",
    "SCHEMA_NAME",
    "SECOND",
    "SECONDARY",
    "SECONDARY_ENGINE",
    "SECONDARY_LOAD",
    "SECONDARY_UNLOAD",
    "SECOND_MICROSECOND",
    "SECURITY",
    "SELECT",
    "SENSITIVE",
    "SEPARATOR",
    "SERIAL",
    "SERIALIZABLE",
    "SERVER",
    "SESSION",
    "SET",
    "SHARE",
    "SHOW",
    "SHUTDOWN",
    "SIGNAL",
    "SIGNED",
    "SIMPLE",
    "SKIP",
    "SLAVE",
    "SLOW",
    "SMALLINT",
    "SNAPSHOT",
    "SOCKET",
    "SOME",
    "SONAME",
    "SOUNDS",
    "SOURCE",
    "SPATIAL",
    "SPECIFIC",
    "SQL",
    "SQLEXCEPTION",
    "SQLSTATE",
    "SQLWARNING",
    "SQL_AFTER_GTIDS",
    "SQL_AFTER_MTS_GAPS",
    "SQL_BEFORE_GTIDS",
    "SQL_BIG_RESULT",
    "SQL_BUFFER_RESULT",
    "SQL_CACHE",
    "SQL_CALC_FOUND_ROWS",
    "SQL_NO_CACHE",
    "SQL_SMALL_RESULT",
    "SQL_THREAD",
    "SQL_TSI_DAY",
    "SQL_TSI_HOUR",
    "SQL_TSI_MINUTE",
    "SQL_TSI_MONTH",
    "SQL_TSI_QUARTER",
    "SQL_TSI_SECOND",
    "SQL_TSI_WEEK",
    "SQL_TSI_YEAR",
    "SRID",
    "SSL",
    "STACKED",
    "START",
    "STARTING",
    "STARTS",
    "STATS_AUTO_RECALC",
    "STATS_PERSISTENT",
    "STATS_SAMPLE_PAGES",
    "STATUS",
    "STOP",
    "STORAGE",
    "STORED",
    "STRAIGHT_JOIN",
    "STRING",
    "SUBCLASS_ORIGIN",
    "SUBJECT",
    "SUBPARTITION",
    "SUBPARTITIONS",
    "SUPER",
    "SUSPEND",
    "SWAPS",
    "SWITCHES",
    "SYSTEM",
    "TABLE",
    "TABLES",
    "TABLESPACE",
    "TABLE_CHECKSUM",
    "TABLE_NAME",
    "TEMPORARY",
    "TEMPTABLE",
    "TERMINATED",
    "TEXT",
    "THAN",
    "THEN",
    "THREAD_PRIORITY",
    "TIES",
    "TIME",
    "TIMESTAMP",
    "TIMESTAMPADD",
    "TIMESTAMPDIFF",
    "TINYBLOB",
    "TINYINT",
    "TINYTEXT",
    "TO",
    "TRAILING",
    "TRANSACTION",
    "TRIGGER",
    "TRIGGERS",
    "TRUE",
    "TRUNCATE",
    "TYPE",
    "TYPES",
    "UNBOUNDED",
    "UNCOMMITTED",
    "UNDEFINED",
    "UNDO",
    "UNDOFILE",
    "UNDO_BUFFER_SIZE",
    "UNICODE",
    "UNINSTALL",
    "UNION",
    "UNIQUE",
    "UNKNOWN",
    "UNLOCK",
    "UNSIGNED",
    "UNTIL",
    "UPDATE",
    "UPGRADE",
    "USAGE",
    "USE",
    "USER",
    "USER_RESOURCES",
    "USE_FRM",
    "USING",
    "UTC_DATE",
    "UTC_TIME",
    "UTC_TIMESTAMP",
    "VALIDATION",
    "VALUE",
    "VALUES",
    "VARBINARY",
    "VARCHAR",
    "VARCHARACTER",
    "VARIABLES",
    "VARYING",
    "VCPU",
    "VIEW",
    "VIRTUAL",
    "VISIBLE",
    "WAIT",
    "WARNINGS",
    "WEEK",
    "WEIGHT_STRING",
    "WHEN",
    "WHERE",
    "WHILE",
    "WINDOW",
    "WITH",
    "WITHOUT",
    "WORK",
    "WRAPPER",
    "WRITE",
    "X509",
    "XA",
    "XID",
    "XML",
    "XOR",
    "YEAR",
    "YEAR_MONTH",
    "ZEROFILL",
    "AVG",
    "BIT_AND",
    "BIT_OR",
    "BIT_XOR",
    "COUNT",
    "COUNT(DISTINCT)",
    "GROUP_CONCAT",
    "JSON_ARRAYAGG",
    "JSON_OBJECTAGG",
    "MAX",
    "MIN",
    "STD",
    "STDDEV",
    "STDDEV_POP",
    "STDDEV_SAMP",
    "SUM",
    "VAR_POP",
    "VAR_SAMP",
    "VARIANCE",
]


def project_has_case_lookup_table(request, project):
    """
    Gets whether a project has a case lookup table
    :param request: Pyramid request object
    :param project: Project ID
    :return: True or False
    """
    res = (
        request.dbsession.query(CaseLookUp.field_name)
        .filter(CaseLookUp.project_id == project)
        .count()
    )
    if res == 0:
        return False
    else:
        return True


def get_project_id_from_name(request, user, project_code):
    res = (
        request.dbsession.query(Project)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Project.project_code == project_code)
        .filter(Userproject.access_type == 1)
        .first()
    )
    if res is not None:
        return res.project_id
    return None


def get_project_access_type(request, user, project_id):
    res = (
        request.dbsession.query(Userproject.access_type)
        .filter(Userproject.user_id == user)
        .filter(Userproject.project_id == project_id)
        .first()
    )
    if res is not None:
        return res.access_type
    else:
        return None


def get_project_code_from_id(request, user, project_id):
    res = (
        request.dbsession.query(Project)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Project.project_id == project_id)
        .filter(Userproject.access_type == 1)
        .first()
    )
    if res is not None:
        return res.project_code
    return None


def get_forms_number(request, project):
    total = (
        request.dbsession.query(Odkform).filter(Odkform.project_id == project).count()
    )
    return total


def get_number_of_case_creators(request, project):
    total = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_casetype == 1)
        .count()
    )
    return total


def get_number_of_case_creators_with_repository(request, project):
    total = (
        request.dbsession.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_casetype == 1)
        .filter(Odkform.form_schema.isnot(None))
        .count()
    )
    return total


def get_case_form(request, project):
    """
    This will return the case form of a project. If the form is merged then it will return any
    because the dictionary and database are the same across merged forms.
    :param request: Pyramid request object
    :param project: FormShare project
    :return: A form ID or None
    """
    res = (
        request.dbsession.query(Odkform.form_id)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_casetype == 1)
        .filter(Odkform.form_schema.isnot(None))
        .first()
    )
    if res is not None:
        return res.form_id
    else:
        return None


def get_case_schema(request, project):
    res = (
        request.dbsession.query(Odkform.form_schema)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_casetype == 1)
        .filter(Odkform.form_schema.isnot(None))
        .first()
    )
    if res is not None:
        return res[0]
    else:
        return None


def get_project_owner(request, project):
    res = (
        request.dbsession.query(Userproject.user_id)
        .filter(Userproject.project_id == project)
        .filter(Userproject.access_type == 1)
        .first()
    )
    if res is not None:
        return res.user_id
    else:
        return None


def is_collaborator(request, user, project, accepted_status=1):
    res = (
        request.dbsession.query(Userproject.user_id)
        .filter(Userproject.project_id == project)
        .filter(Userproject.user_id == user)
        .filter(Userproject.project_accepted == accepted_status)
        .first()
    )
    if res is not None:
        return True
    else:
        return False


def get_owned_project(request, user):
    res = (
        request.dbsession.query(Project)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Userproject.access_type == 1)
        .all()
    )
    return map_from_schema(res)


def get_user_projects(request, user, logged_user):
    if user == logged_user:
        # The logged account is the user account = Seeing my projects
        res = (
            request.dbsession.query(Project, Userproject)
            .filter(Project.project_id == Userproject.project_id)
            .filter(Userproject.user_id == user)
            .filter(Userproject.project_accepted == 1)
            .all()
        )
        projects = map_from_schema(res)
    else:
        projects = []
        # The logged account is different as the user account =  Seeing someone else projects

        # Get all the projects of that user
        all_user_projects = (
            request.dbsession.query(Project)
            .filter(Project.project_id == Userproject.project_id)
            .filter(Userproject.user_id == user)
            .filter(Userproject.project_accepted == 1)
            .all()
        )
        all_user_projects = map_from_schema(all_user_projects)
        for project in all_user_projects:
            # Check each project to see if the logged user collaborate with it
            res = (
                request.dbsession.query(Project, Userproject)
                .filter(Project.project_id == Userproject.project_id)
                .filter(Userproject.user_id == logged_user)
                .filter(Userproject.project_id == project["project_id"])
                .filter(Userproject.project_accepted == 1)
                .first()
            )
            collaborative_project = map_from_schema(res)
            if collaborative_project:
                collaborative_project["collaborate"] = True
                collaborative_project["user_id"] = user
                projects.append(collaborative_project)
            else:
                if project["project_public"] == 1:
                    project["collaborate"] = False
                    project["access_type"] = 5
                    projects.append(project)

    for project in projects:
        submissions, last, by, form = get_dataset_stats_for_project(
            request.registry.settings, user, project["project_code"]
        )
        if last is not None:
            project["last_submission"] = dateutil.parser.parse(last)
        else:
            project["last_submission"] = None
        project["total_submissions"] = submissions
        project["last_submission_by"] = by
        project["last_submission_by_details"] = get_by_details(
            request, user, project["project_id"], by
        )
        project["last_submission_form"] = form
        project["last_submission_form_details"] = get_form_data(
            request, project["project_id"], form
        )
        project["total_forms"] = get_forms_number(request, project["project_id"])
        project["owner"] = get_project_owner(request, project["project_id"])
        project["total_case_creators"] = get_number_of_case_creators(
            request, project["project_id"]
        )
        project[
            "total_case_creators_with_repository"
        ] = get_number_of_case_creators_with_repository(request, project["project_id"])
        project["case_form"] = get_case_form(request, project["project_id"])
        project["case_schema"] = get_case_schema(request, project["project_id"])
        project["has_case_lookup_table"] = project_has_case_lookup_table(
            request, project["project_id"]
        )

    projects = sorted(projects, key=lambda prj: project["project_cdate"], reverse=True)
    return projects


def get_active_project(request, user):
    res = (
        request.dbsession.query(Project, Userproject)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Userproject.project_active == 1)
        .filter(Userproject.project_accepted == 1)
        .first()
    )
    mapped_data = map_from_schema(res)
    user_projects = get_user_projects(request, user, user)
    if res is not None:
        for project in user_projects:
            if project["project_id"] == mapped_data["project_id"]:
                mapped_data["access_type"] = project["access_type"]
                mapped_data["owner"] = project["owner"]
    else:
        if (
            len(user_projects) > 0
        ):  # pragma: no cover   . TODO: Monitor if error appears in logs
            log.error("Possible unused code used. URL {}".format(request.url))
            last_project = (
                request.dbsession.query(Userproject)
                .filter(Userproject.user_id == user)
                .filter(Userproject.project_accepted == 1)
                .order_by(Userproject.access_date.desc())
                .first()
            )
            if last_project is not None:
                last_project_id = last_project.project_id
                request.dbsession.query(Userproject).filter(
                    Userproject.user_id == user
                ).filter(Userproject.project_id == last_project_id).update(
                    {"project_active": 1}
                )
                try:
                    request.dbsession.flush()
                except Exception as e:
                    request.dbsession.rollback()
                    log.error("Error {} while getting an active project".format(str(e)))

                res = (
                    request.dbsession.query(Project, Userproject)
                    .filter(Project.project_id == Userproject.project_id)
                    .filter(Userproject.user_id == user)
                    .filter(Userproject.project_active == 1)
                    .filter(Userproject.project_accepted == 1)
                    .first()
                )
                mapped_data = map_from_schema(res)
                if res is not None:
                    for project in user_projects:
                        if project["project_id"] == mapped_data["project_id"]:
                            mapped_data["access_type"] = project["access_type"]
                            mapped_data["owner"] = project["owner"]

    return mapped_data


def add_project(request, user, project_data):
    _ = request.translate
    res = (
        request.dbsession.query(Project)
        .filter(Project.project_id == Userproject.project_id)
        .filter(Userproject.user_id == user)
        .filter(Userproject.access_type == 1)
        .filter(Project.project_code == project_data["project_code"])
        .first()
    )
    if res is None:
        if "project_id" not in project_data.keys():
            project_data["project_id"] = str(uuid.uuid4())
        project_data["project_cdate"] = datetime.datetime.now()

        mapped_data = map_to_schema(Project, project_data)
        new_project = Project(**mapped_data)
        try:
            request.dbsession.add(new_project)
            request.dbsession.flush()

            request.dbsession.query(Userproject).filter(
                Userproject.user_id == user
            ).update({"project_active": 0})

            new_access = Userproject(
                user_id=user,
                project_id=project_data["project_id"],
                access_type=1,
                access_date=project_data["project_cdate"],
                project_active=1,
                project_accepted=1,
                project_accepted_date=project_data["project_cdate"],
            )
            try:
                request.dbsession.add(new_access)
                request.dbsession.flush()
            except IntegrityError:
                request.dbsession.rollback()
                log.error(
                    "Duplicated access for user {} in project {}".format(
                        user, mapped_data["project_id"]
                    )
                )
                return False, _("Error allocating access")
            except Exception as e:
                request.dbsession.rollback()
                log.error(
                    "Error {} while allocating access for user {} in project {}".format(
                        str(e), user, mapped_data["project_id"]
                    )
                )
                return False, str(e)
            return True, project_data["project_id"]
        except IntegrityError:
            request.dbsession.rollback()
            log.error("Duplicated project {}".format(mapped_data["project_id"]))
            return False, _("The project already exists")
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while inserting project {}".format(
                    str(e), mapped_data["project_id"]
                )
            )
            return False, str(e)
    else:
        return (
            False,
            _("A project with name '{}' already exists in your account").format(
                project_data["project_code"]
            ),
        )


def modify_project(request, project, project_data):
    if project_data.get("project_code", None) is not None:
        project_data.pop("project_code")
    mapped_data = map_to_schema(Project, project_data)
    try:
        request.dbsession.query(Project).filter(Project.project_id == project).update(
            mapped_data
        )
        request.dbsession.flush()
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while updating project {}".format(str(e), project))
        return False, str(e)
    return True, ""


def delete_project(request, user, project):
    _ = request.translate
    try:
        request.dbsession.query(Project).filter(Project.project_id == project).delete()
        request.dbsession.flush()
        res = (
            request.dbsession.query(Userproject)
            .filter(Userproject.user_id == user)
            .filter(Userproject.project_active == 1)
            .first()
        )
        if res is None:
            res = (
                request.dbsession.query(Userproject)
                .filter(Userproject.user_id == user)
                .order_by(Userproject.access_date.desc())
                .first()
            )
            if res is not None:
                new_active_project = res.project_id
                request.dbsession.query(Userproject).filter(
                    Userproject.user_id == user
                ).filter(Userproject.project_id == new_active_project).update(
                    {"project_active": 1}
                )
                request.dbsession.flush()
    except IntegrityError as e:
        request.dbsession.rollback()
        log.error("Error {} while deleting project {}".format(str(e), project))
        return (
            False,
            _(
                "If you have forms with submissions, first you need to delete such forms"
            ),
        )
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while deleting project {}".format(str(e), project))
        return False, str(e)
    return True, ""


def set_project_as_active(request, user, project):
    try:
        request.dbsession.query(Userproject).filter(Userproject.user_id == user).update(
            {"project_active": 0}
        )
        request.dbsession.flush()
        request.dbsession.query(Userproject).filter(Userproject.user_id == user).filter(
            Userproject.project_id == project
        ).update({"project_active": 1})
        request.dbsession.flush()
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while setting project {} as active".format(str(e), project))
        return False, str(e)
    return True, ""


def add_file_to_project(request, project, file_name, overwrite=False):
    _ = request.translate
    res = (
        request.dbsession.query(ProjectFile)
        .filter(ProjectFile.project_id == project)
        .filter(ProjectFile.file_name == file_name)
        .first()
    )
    if res is None:
        new_file_id = str(uuid.uuid4())
        new_file = ProjectFile(
            file_id=new_file_id,
            project_id=project,
            file_name=file_name,
            file_udate=datetime.datetime.now(),
        )
        try:
            request.dbsession.add(new_file)
            request.dbsession.flush()
        except Exception as e:
            request.dbsession.rollback()
            log.error(
                "Error {} while adding file {} in project {}".format(
                    str(e), file_name, project
                )
            )
            return False, str(e)
        return True, new_file_id
    else:
        if not overwrite:
            return False, _("The file {} already exist").format(file_name)
        else:
            return True, res.file_id


def get_project_files(request, project):
    res = (
        request.dbsession.query(ProjectFile)
        .filter(ProjectFile.project_id == project)
        .all()
    )
    return map_from_schema(res)


def remove_file_from_project(request, project, file_name):
    try:
        request.dbsession.query(ProjectFile).filter(
            ProjectFile.project_id == project
        ).filter(ProjectFile.file_name == file_name).delete()
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error(
            "Error {} while removing file {} in project {}".format(
                str(e), file_name, project
            )
        )
        return False, str(e)


def get_project_details(request, project):
    res = request.dbsession.query(Project).filter(Project.project_id == project).first()
    if res is not None:
        return map_from_schema(res)
    else:
        return None
