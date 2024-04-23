from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import logging
from formshare.processes.email.send_email import send_error_to_technical_team
import time

log = logging.getLogger("formshare")


class CreateConnectionError(Exception):
    """
    Exception raised when there is an error while creating the connection.
    """


class DatabaseConnection:
    def __init__(self, engine, connection):
        self.engine = engine
        self._connection = connection

    def disconnect(self):
        self.connection.invalidate()
        self.engine.dispose()

    @property
    def connection(self):
        return self._connection


def get_db_connection(request):
    engine_on = False
    connection_on = False
    engine = None
    connection = None
    num_intents = 1
    while not connection_on and num_intents <= 3:
        try:
            engine = create_engine(
                request.registry.settings.get("sqlalchemy.url"), poolclass=NullPool
            )
            engine_on = True
            connection = engine.connect()
            connection_on = True
        except Exception as ee:
            error_message = (
                "Unable to create secondary connection. Intent: {}\n"
                "Error: {}".format(num_intents, str(ee))
            )
            log.error(error_message)
            send_error_to_technical_team(request, error_message)
            if engine_on:
                engine.dispose()
            num_intents = num_intents + 1
            time.sleep(2)
    if connection is None:
        raise CreateConnectionError(
            "FormShare was not able to create a connection to MySQL after 3 attempts."
        )
    return DatabaseConnection(engine, connection)
