import pika
import json


def send_task_status_to_form(sse_project_id, sse_form_id, task_id, status):
    try:
        if sse_project_id is not None and sse_form_id is not None:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
            channel = connection.channel()
            parts = ['formshare', sse_project_id, sse_form_id]
            channel.queue_declare(queue='_'.join(parts))
            dict_body = {'task': task_id, 'status': status}
            channel.basic_publish(exchange='', routing_key='_'.join(parts), body=json.dumps(dict_body))
            connection.close()
    except Exception as e:
        print(str(e))
