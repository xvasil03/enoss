from swift.common.http import is_success
from swift.common.swob import wsgify
from swift.common.utils import split_path, get_logger
from swift.common.request_helpers import get_sys_meta_prefix
from swift.proxy.controllers.base import get_container_info, get_account_info, get_object_info
from eventlet import Timeout
import six
import json

from swift.common.wsgi import WSGIContext
from swift.common.swob import Request

import swift.common.middleware.event_notifications.destination as destination_module

from swift.common.middleware.event_notifications.configuration import S3ConfigurationValidator, S3NotifiationConfiguration
from swift.common.middleware.event_notifications.payload import S3NotificationPayload
from swift.common.middleware.event_notifications.destination import BeanstalkdDestination

from pystalkd.Beanstalkd import Connection as BeanstalkdConnection

class EventNotificationsMiddleware(WSGIContext):
    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.logger = get_logger(conf, log_route='eventnotifications')
        self.configuration_validator = S3ConfigurationValidator('/usr/local/src/swift/swift/common/middleware/event_notifications/configuration-schema.json')
        self.s3_payload = S3NotificationPayload(self.conf)
        self.destinations = {}
        for destination_name, destination_conf in json.loads(self.conf.get("destinations", {})).items():
            destination_class = getattr(destination_module, destination_module.get_destination_class_name(destination_conf["handler"]))
            self.destinations[destination_name] = destination_class(destination_conf)

        super(EventNotificationsMiddleware, self).__init__(app)

    @wsgify
    def __call__(self, req):
        event_configation_changed = False
        if req.method == "POST" and req.query_string == "notification":
            config = req.body_file.read()
            if self.configuration_validator.validate(config):
                req.headers[get_sys_meta_prefix('container') + 'notifications'] = config
                event_configation_changed = True
        # swift can call it self recursively => we want only one notification per user request
        req.headers["X-Backend-EventNotification-Ignore"] = True
        resp = req.get_response(self.app)

        try:
            if not resp.headers.get("X-Backend-EventNotification-Ignore"):
                container = get_container_info(resp.environ, self.app)
                event_notifications_configuration = container.get("sysmeta", {}).get("notifications")

                if event_notifications_configuration:
                    s3_configuration = S3NotifiationConfiguration(event_notifications_configuration)
                    for destination_name, destination_configuration in s3_configuration.get_satisfied_destinations(self.app, resp).items():
                        destination_handler = self.destinations[destination_name]
                        payload = self.s3_payload.create_test_payload(self.app, resp) if event_configation_changed else self.s3_payload.create_payload(self.app, resp)
                        destination_handler.send_notification(destination_configuration, payload)
        except Exception as e:
            self.destinations["beanstalkd"].connection.put(str(e))

        return resp


def event_notifications_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    def event_notifications_filter(app):
        return EventNotificationsMiddleware(app, conf)
    return event_notifications_filter
