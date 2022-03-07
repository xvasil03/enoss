from swift.common.http import is_success
from swift.common.swob import wsgify
from swift.common.utils import split_path, get_logger
from swift.common.request_helpers import get_sys_meta_prefix
from swift.proxy.controllers.base import get_container_info, get_account_info, get_object_info
from eventlet import Timeout
import six
import json

from swift.common.wsgi import WSGIContext
from swift.common.swob import Request, Response

import swift.common.middleware.event_notifications.destination as destination_module
import swift.common.middleware.event_notifications.payload as payload_module

from swift.common.middleware.event_notifications.configuration import S3ConfigurationValidator, S3NotifiationConfiguration
from swift.common.middleware.event_notifications.destination import BeanstalkdDestination
from swift.common.middleware.event_notifications.utils import get_payload_handlers, get_destination_handlers, \
    get_payload_handler_name, get_destination_handler_name

from pystalkd.Beanstalkd import Connection as BeanstalkdConnection

class EventNotificationsMiddleware(WSGIContext):
    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.logger = get_logger(conf, log_route='eventnotifications')
        self.configuration_validator = S3ConfigurationValidator('/usr/local/src/swift/swift/common/middleware/event_notifications/configuration-schema.json')
        self.destination_handlers = {}
        destinations_conf = json.loads(self.conf.get("destinations", {}))
        self.destination_handlers = {destination_handler_name: destination_handler(destinations_conf) \
            for destination_handler_name, destination_handler in get_destination_handlers([destination_module]).items()}
        self.payload_handlers = {payload_handler_name: payload_handler(self.conf) \
            for payload_handler_name, payload_handler in get_payload_handlers([payload_module]).items()}
        super(EventNotificationsMiddleware, self).__init__(app)

    @wsgify
    def __call__(self, req):

        try:
            event_configation_changed = False
            if req.method == "POST" and req.query_string == "notification":
                config = req.body_file.read().strip()
                if not config:
                    req.headers[get_sys_meta_prefix('container') + 'notifications'] = ""
                else:
                    if self.configuration_validator.validate(self.destination_handlers, config):
                        req.headers[get_sys_meta_prefix('container') + 'notifications'] = config
                    else:
                        # todo: send info about which part of configuration is invalid
                        return Response(request=req, status=400, body=b"Invalid configuration", content_type="text/plain")
                event_configation_changed = True
            # swift can call it self recursively => we want only one notification per user request
            req.headers["X-Backend-EventNotification-Ignore"] = True
            resp = req.get_response(self.app)
        except Exception as e:
            self.destination_handlers[get_destination_handler_name("beanstalkd")].connection.put("1:" + str(e))

        try:
            if not resp.headers.get("X-Backend-EventNotification-Ignore"):

                container = get_container_info(resp.environ, self.app)
                event_notifications_configuration = container.get("sysmeta", {}).get("notifications")

                if event_notifications_configuration:
                    s3_configuration = S3NotifiationConfiguration(event_notifications_configuration)
                    for destination_name, destination_configurations in s3_configuration.get_satisfied_destinations(self.app, resp).items():
                        destination_handler = self.destination_handlers[get_destination_handler_name(destination_name)]
                        for destination_configuration in destination_configurations:
                            payload_handler = self.payload_handlers[get_payload_handler_name(destination_configuration.payload_type)]
                            payload = payload_handler.create_test_payload(self.app, resp) if event_configation_changed else payload_handler.create_payload(self.app, resp)
                            destination_handler.send_notification(destination_configuration, payload)
                if req.method == "GET" and req.query_string.startswith("notification") and resp.is_success: #todo ACL
                    resp.body = str.encode(str(json.loads(event_notifications_configuration)) + '\n' \
                        if event_notifications_configuration else "")

        except Exception as e:
            self.destination_handlers[get_destination_handler_name("beanstalkd")].connection.put("2:" + str(e))

        return resp


def event_notifications_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    def event_notifications_filter(app):
        return EventNotificationsMiddleware(app, conf)
    return event_notifications_filter
