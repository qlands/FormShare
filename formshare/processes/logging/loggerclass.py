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


def masked_command(args):
    """A tool's command line, as a list of arguments, with the database
    password masked: for a record kept beside a submission's log, which the
    logger's own masking never sees. RSTools takes the password as "-p
    <password>" in one argument, or as "-p=<password>"."""
    masked = []
    for an_arg in args:
        if an_arg.startswith("-p ") or an_arg.startswith("-p="):
            masked.append(an_arg[:3] + "xxxxxxxx")
        else:
            masked.append(an_arg)
    return " ".join(masked)
