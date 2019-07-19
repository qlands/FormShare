from .classes import PrivateView
from pyramid.httpexceptions import HTTPNotFound
from formshare.processes.db import get_project_id_from_name
from pyramid.response import Response
import json
import time
import random
import logging
import datetime
import transaction
from formshare.models import get_engine, get_session_factory, get_tm_session, TaskMessages, Product


log = logging.getLogger("formshare")


def safe_exit(then, project_id, form_id):
    """
    This prevents the SSE from sending events to a void. Will stop after 10 minutes. If after 10 minutes the SSE client
    is alive then the SSE client will try to connect and no harm is done.
    :param then: Start time of the generator
    :param project_id: Project ID
    :param form_id: Form ID
    :return: True if the SSE should stop
    """
    now = datetime.datetime.now()
    duration = now - then
    duration_in_s = duration.total_seconds()
    minutes = divmod(duration_in_s, 60)[0]
    if minutes > 10:
        log.error("Safe SSE exit for project {}, form {}".format(project_id, form_id))
        return True
    else:
        return False


def message_generator(settings, project_id, form_id):
    generator_start_time = datetime.datetime.now()
    ids_sent = []
    since = datetime.datetime.now() - datetime.timedelta(hours=24)
    while True and not safe_exit(generator_start_time, project_id, form_id):
        try:
            session_factory = get_session_factory(get_engine(settings))
            with transaction.manager:
                db_session = get_tm_session(session_factory, transaction.manager)
                last_message = db_session.query(TaskMessages.message_id,
                                                Product.celery_taskid, TaskMessages.message_content).\
                    filter(TaskMessages.celery_taskid == Product.celery_taskid).\
                    filter(Product.project_id == project_id).filter(Product.form_id == form_id).\
                    filter(TaskMessages.message_date >= since).order_by(TaskMessages.message_date.asc()).all()
                if last_message is not None:
                    to_send = []
                    for message in last_message:
                        if message.message_id not in ids_sent:
                            ids_sent.append(message.message_id)
                            to_send.append(message.message_content)
                    if len(to_send) > 0:
                        for a_message in to_send:
                            msg = "data: %s\n\n" % json.dumps({'message': a_message})
                            yield msg.encode()
                    else:
                        msg = "data: %s\n\n" % json.dumps({'message': None})
                        yield msg.encode()
                    time.sleep(random.randint(1, 10))
                else:
                    msg = "data: %s\n\n" % json.dumps({'message': None})
                    yield msg.encode()
                    time.sleep(random.randint(1, 10))
        except Exception as e:
            log.error(
                "Error in SSE generator for project {}, form {}. Error: {}".format(project_id, form_id, str(e)))
            msg = "data: %s\n\n" % json.dumps({'message': "error {}".format(str(e))})
            yield msg.encode()
            time.sleep(random.randint(1, 10))


class SSEventStream(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict['userid']
        project_code = self.request.matchdict['projcode']
        form_id = self.request.matchdict['formid']
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        project_details = {}
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
                    project_details = project
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        if project_details["access_type"] >= 4:
            raise HTTPNotFound

        headers = [('Content-Type', 'text/event-stream'),
                   ('Cache-Control', 'no-cache')]
        response = Response(headerlist=headers)
        settings = {}
        for key, value in self.request.registry.settings.items():
            if isinstance(value, str):
                settings[key] = value

        response.app_iter = message_generator(settings, project_id, form_id)
        return response
