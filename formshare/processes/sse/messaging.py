import logging

import paho.mqtt.publish as publish

log = logging.getLogger("formshare")


def send_task_status_to_form(settings, task_id, status):
    if settings.get("mosquitto.host", None) is not None:
        auth = {
            "username": settings.get("mosquitto.user", ""),
            "password": settings.get("mosquitto.password", ""),
        }
        mqtt_host = settings.get("mosquitto.host", None)
        mqtt_port = int(settings.get("mosquitto.port", "1883"))
        try:
            publish.single(
                "formshare/tasks/{}".format(task_id),
                status,
                hostname=mqtt_host,
                port=mqtt_port,
                auth=auth,
            )
        except Exception as e:
            log.error("Unable to publish status. Error: {}".format(str(e)))
    else:
        log.error("MQTT server is not available. Task messages are not possible")
