import logging
from formshare.config.celery_app import get_ini_value


class SecretLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        self.db_password = get_ini_value("mysql.password")
        super(SecretLogger, self).__init__(name, level)

    def info(self, msg, *args, **kwargs):
        message = msg.replace(self.db_password, "xxxxxxxx")
        super(SecretLogger, self).info(message, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        message = msg.replace(self.db_password, "xxxxxxxx")
        super(SecretLogger, self).error(message, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        message = msg.replace(self.db_password, "xxxxxxxx")
        super(SecretLogger, self).warning(message, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        message = msg.replace(self.db_password, "xxxxxxxx")
        super(SecretLogger, self).debug(message, *args, **kwargs)
