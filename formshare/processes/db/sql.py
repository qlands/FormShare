from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import logging
from formshare.processes.logging.loggerclass import SecretLogger

logging.setLoggerClass(SecretLogger)
log = logging.getLogger("formshare")


def execute_dml_sql(request, sql):
    sqlalchemy_url = request.registry.settings.get("sqlalchemy.url")
    engine = None
    try:
        engine = create_engine(sqlalchemy_url, poolclass=NullPool)
        connection = None
        try:
            connection = engine.connect()
            try:
                connection.execute(sql)
            except Exception as e:
                log.error("Cannot execute sql:\n {} \nError: {}".format(sql, str(e)))
        except Exception as e:
            log.error(
                "Cannot create connection for DML execution. Error: {}".format(str(e))
            )
        if connection is not None:
            connection.invalidate()

    except Exception as e:
        log.error("Cannot create engine for DML execution. Error: {}".format(str(e)))
    if engine is not None:
        engine.dispose()
