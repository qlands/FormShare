import os
import logging
from formshare.processes.logging.loggerclass import SecretLogger
from formshare.models.formshare import (
    Base,
    Collaboratorlog,
    User,
    Userlog,
    Project,
    Collaborator,
    Collgroup,
    Odkform,
    Collingroup,
    Formacces,
    Formgrpacces,
    Jsonlog,
    Submission,
    Jsonhistory,
    Userproject,
    ProjectFile,
    MediaFile,
    Product,
    FinishedTask,
    Settings,
    ProjectSettings,
    FormSettings,
    DictTable,
    DictField,
    CaseLookUp,
    Partner,
    PartnerProject,
    PartnerForm,
    TimeZone,
    Tenant,
    Roles,
    UserRoles,
    CookieConsent,
    CookieConsentLog,
)
from formshare.models.schema import *
from sqlalchemy import engine_from_config, text
from sqlalchemy.orm import configure_mappers
from sqlalchemy.orm import sessionmaker
from formshare.plugins.core import PluginImplementations
from formshare.plugins.interfaces import IRoles

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")

# import or define all models here to ensure they are attached to the
# Base.metadata prior to any initialization routines

# run configure_mappers after defining all of the models to ensure
# all relationships can be setup
configure_mappers()


def get_engine(settings, prefix="sqlalchemy."):
    pool_size = int(settings.get("pool.size", "30"))
    max_overflow = int(settings.get("pool.max.overflow", "10"))
    pool_recycle = int(settings.get("pool.recycle", "2000"))
    pool_pre_ping = settings.get("pool.pre.ping", "false")
    if pool_pre_ping == "false":
        pool_pre_ping = False
    else:
        pool_pre_ping = True
    engine = engine_from_config(
        settings,
        prefix,
        pool_recycle=pool_recycle,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
    )
    return engine


def get_session_factory(engine):
    factory = sessionmaker()
    factory.configure(bind=engine)
    Base.metadata.bind = engine
    return factory


def startup_tasks(engine, settings):
    """
    Run one-time startup tasks after the engine is created.

    Previously called via Pyramid's includeme() hook; now called directly
    from the FastAPI app factory (formshare.app.create_app).
    """
    with engine.connect() as conn:
        # Purge old binary logs (best-effort, non-fatal)
        try:
            conn.execute(text("PURGE BINARY LOGS BEFORE '2999-12-12 23:59:59';"))
        except Exception as e:
            log.error("Unable to purge binary logs. Error: {}".format(str(e)))

        # Write a DROP script for any leftover TMP_* tables in FS_* schemas
        config_file = settings.get("global:config:file", "")
        if config_file:
            path_to_init_file = os.path.dirname(os.path.realpath(config_file))
            try:
                schemas = conn.execute(text("SHOW SCHEMAS")).fetchall()
                with open(path_to_init_file + "/temp_tables.log", "w") as myfile:
                    for an_schema in schemas:
                        if an_schema[0].find("FS_") == 0:
                            tables = conn.execute(
                                text("SHOW TABLES FROM {}".format(an_schema[0]))
                            ).fetchall()
                            for a_table in tables:
                                if a_table[0].find("TMP_") == 0:
                                    myfile.write(
                                        "DROP TABLE {}.{};\n".format(
                                            an_schema[0], a_table[0]
                                        )
                                    )
            except Exception as e:
                log.error(
                    "Unable to scan schemas for temp tables. Error: {}".format(str(e))
                )

        # Insert any plugin-defined roles (INSERT IGNORE — safe to repeat)
        plugins_roles = []
        for plugin in PluginImplementations(IRoles):
            plugin_roles = plugin.get_roles(settings)
            plugins_roles = plugins_roles + plugin_roles
        for a_role in plugins_roles:
            sql = text(
                "INSERT IGNORE INTO role (role_id, role_name) VALUES (:role_id, :role_name)"
            )
            try:
                conn.execute(
                    sql,
                    {"role_id": a_role["role_id"], "role_name": a_role["role_name"]},
                )
            except Exception as e:
                log.error(
                    "Unable to add role {} Error: {}".format(a_role["role_id"], str(e))
                )

    initialize_schema()
