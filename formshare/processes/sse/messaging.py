import json
from formshare.models import (
    get_engine,
    get_session_factory,
    get_tm_session,
    TaskMessages,
)
import transaction
import uuid
import datetime
import logging

log = logging.getLogger("formshare")


def send_task_status_to_form(settings, task_id, status):
    try:
        session_factory = get_session_factory(get_engine(settings))
        with transaction.manager:
            dict_body = {"task": task_id, "status": status}
            body_string = json.dumps(dict_body)
            db_session = get_tm_session(session_factory, transaction.manager)
            message_id = str(uuid.uuid4())
            new_message = TaskMessages(
                message_id=message_id,
                celery_taskid=task_id,
                message_date=datetime.datetime.now(),
                message_content=body_string,
            )
            try:
                db_session.add(new_message)
                db_session.flush()
            except Exception as e:
                log.error(
                    "Error {} while adding a new message to task {}".format(
                        str(e), task_id
                    )
                )
                return False, str(e)

    except Exception as e:
        print(str(e))
