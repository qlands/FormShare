from .classes import PrivateView
from pyramid.httpexceptions import HTTPNotFound
from formshare.processes.db import get_project_id_from_name
from pyramid.response import Response
import json
import pika
import time
import random
import logging
import datetime


log = logging.getLogger(__name__)


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


def message_generator(project_id, form_id):
    generator_start_time = datetime.datetime.now()
    while True and not safe_exit(generator_start_time, project_id, form_id):
        query_messages = True
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        except Exception as e:
            log.error(
                "Error connecting to messaging service for project {}, form {}. Error: {}".format(project_id, form_id,
                                                                                                  str(e)))
            query_messages = False
            connection = None
        if query_messages:
            try:
                channel = connection.channel()
                parts = ['formshare', project_id, form_id]
                channel.queue_declare(queue='_'.join(parts))
                method_frame, header_frame, body = channel.basic_get('_'.join(parts))
                if method_frame:
                    channel.basic_ack(method_frame.delivery_tag)
                    try:
                        msg = "data: %s\n\n" % json.dumps({'message': body.decode()})
                    except Exception as e:
                        msg = "data: %s\n\n" % json.dumps({'message': "error {}".format(str(e))})
                    connection.close()
                    yield msg.encode()
                    time.sleep(random.randint(1, 10))
                else:
                    connection.close()
                    msg = "data: %s\n\n" % json.dumps({'message': None})
                    yield msg.encode()
                    time.sleep(random.randint(1, 10))
            except Exception as e:
                connection.close()
                log.error(
                    "Error in SSE generator for project {}, form {}. Error: {}".format(project_id, form_id, str(e)))
                msg = "data: %s\n\n" % json.dumps({'message': "error {}".format(str(e))})
                yield msg.encode()
                time.sleep(random.randint(1, 10))
        else:
            msg = "data: %s\n\n" % json.dumps({'message': "The messaging service is not available for "
                                                          "project {}, form {}".format(project_id, form_id)})
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
        if project_id is not None:
            project_found = False
            for project in self.user_projects:
                if project["project_id"] == project_id:
                    project_found = True
            if not project_found:
                raise HTTPNotFound
        else:
            raise HTTPNotFound

        headers = [('Content-Type', 'text/event-stream'),
                   ('Cache-Control', 'no-cache')]
        response = Response(headerlist=headers)
        response.app_iter = message_generator(project_id, form_id)
        return response
