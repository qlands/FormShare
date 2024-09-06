import os
import logging
from formshare.processes.logging.loggerclass import SecretLogger
import zope.sqlalchemy
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
)
from formshare.models.schema import *
from sqlalchemy import engine_from_config
from sqlalchemy.orm import configure_mappers
from sqlalchemy.orm import sessionmaker

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
    engine = engine_from_config(
        settings,
        prefix,
        pool_recycle=pool_recycle,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )
    return engine


def get_session_factory(engine):
    factory = sessionmaker()
    factory.configure(bind=engine)
    Base.metadata.bind = engine
    return factory


def get_tm_session(session_factory, transaction_manager):
    """
    Get a ``sqlalchemy.orm.Session`` instance backed by a transaction.

    This function will hook the session to the transaction manager which
    will take care of committing any changes.

    - When using pyramid_tm it will automatically be committed or aborted
      depending on whether an exception is raised.

    - When using scripts you should wrap the session in a manager yourself.
      For example::

          import transaction

          engine = get_engine(settings)
          session_factory = get_session_factory(engine)
          with transaction.manager:
              dbsession = get_tm_session(session_factory, transaction.manager)

    """
    dbsession = session_factory()
    zope.sqlalchemy.register(dbsession, transaction_manager=transaction_manager)
    return dbsession


def includeme(config):
    """
    Initialize the model for a Pyramid app.

    Activate this setup using ``config.include('formshare.models')``.

    """
    settings = config.get_settings()
    settings["tm.manager_hook"] = "pyramid_tm.explicit_manager"

    # use pyramid_tm to hook the transaction lifecycle to the request
    config.include("pyramid_tm")

    # use pyramid_retry to retry a request when transient exceptions occur
    config.include("pyramid_retry")
    engine = get_engine(settings)
    try:
        engine.execute("PURGE BINARY LOGS BEFORE '2999-12-12 23:59:59';")
    except Exception as e:
        log.error("Unable to purge binary logs. Error: {}".format(str(e)))
    schemas = engine.execute("show schemas").fetchall()
    path_to_init_file = os.path.dirname(
        os.path.realpath(settings["global:config:file"])
    )
    with open(path_to_init_file + "/temp_tables.log", "w") as myfile:
        for an_schema in schemas:
            if an_schema[0].find("FS_") == 0:
                tables = engine.execute(
                    "SHOW TABLES FROM {}".format(an_schema[0])
                ).fetchall()
                for a_table in tables:
                    if a_table[0].find("TMP_") == 0:
                        myfile.write(
                            "DROP TABLE {}.{};\n".format(an_schema[0], a_table[0])
                        )
    session_factory = get_session_factory(engine)
    config.registry["dbsession_factory"] = session_factory
    config.registry["dbsession_metadata"] = Base.metadata

    # make request.dbsession available for use in Pyramid
    config.add_request_method(
        # r.tm is the transaction manager used by pyramid_tm
        lambda r: get_tm_session(session_factory, r.tm),
        "dbsession",
        reify=True,
    )

    initialize_schema()
