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

import swift.common.middleware.enoss.destinations as destinations_module
import swift.common.middleware.enoss.payloads as payloads_module

from swift.common.middleware.enoss.configuration import S3ConfigurationValidator, S3NotifiationConfiguration
from swift.common.middleware.enoss.utils import get_payload_handlers, get_destination_handlers, \
    get_payload_handler_name, get_destination_handler_name

from pystalkd.Beanstalkd import Connection as BeanstalkdConnection

class ENOSSMiddleware(WSGIContext):
    def __init__(self, app, conf, logger=None):
        self.app = app
        self.conf = conf
        self.logger = logger or get_logger(conf, log_route='eventnotifications')
        self.configuration_validator = S3ConfigurationValidator(self.conf["s3_schema"])
        self.destination_handlers = {}
        destinations_conf = json.loads(self.conf.get("destinations", "{}"))
        self.destination_handlers = {destination_handler_name: destination_handler(destinations_conf) \
            for destination_handler_name, destination_handler in get_destination_handlers([destinations_module]).items()}
        self.payload_handlers = {payload_handler_name: payload_handler(self.conf) \
            for payload_handler_name, payload_handler in get_payload_handlers([payloads_module]).items()}
        super(ENOSSMiddleware, self).__init__(app)

    def get_notification_configuration(self, info_method, environ):
        info = info_method(environ, self.app)
        event_notifications_configuration = info.get("sysmeta", {}).get("notifications")
        return event_notifications_configuration

    def get_current_level(self, account, container, object):
        if object:
            return "object"
        elif container:
            return "container"
        elif account:
            return "account"
        else:
            return None

    def get_upper_level(self, account, container, object):
        if object:
            return "container"
        elif container:
            return "account"
        else:
            return None

    def send_test_notification(self, curr_level, req):
        # todo check if curr_level is not None
        info_method = get_container_info if curr_level == "container" else get_account_info
        event_notifications_configuration = self.get_notification_configuration(info_method, req.environ)
        if event_notifications_configuration:
            s3_configuration = S3NotifiationConfiguration(event_notifications_configuration)
            for destination_name, destination_configurations in s3_configuration.destinations_configurations.items():
                destination_handler = self.destination_handlers[get_destination_handler_name(destination_name)]
                for destination_configuration in destination_configurations:
                    payload_handler = self.payload_handlers[get_payload_handler_name(destination_configuration.payload_type)]
                    payload = payload_handler.create_test_payload(self.app, req, destination_configuration)
                    destination_handler.send_notification(payload)

    def send_notification(self, upper_level, req):
        # todo check if upper_level is not None
        info_method = get_container_info if upper_level == "container" else get_account_info
        event_notifications_configuration = self.get_notification_configuration(info_method, req.environ)
        if event_notifications_configuration:
            s3_configuration = S3NotifiationConfiguration(event_notifications_configuration)
            for destination_name, destination_configurations in s3_configuration.get_satisfied_destinations(self.app, req).items():
                destination_handler = self.destination_handlers[get_destination_handler_name(destination_name)]
                for destination_configuration in destination_configurations:
                    payload_handler = self.payload_handlers[get_payload_handler_name(destination_configuration.payload_type)]
                    payload = payload_handler.create_payload(self.app, req, destination_configuration)
                    destination_handler.send_notification(payload)

    @wsgify
    def __call__(self, req):
        if req.headers.get("X-Backend-EventNotification-Ignore"):
            return req.get_response(self.app)
        # swift can call it self recursively => we want only one notification per user request
        req.headers["X-Backend-EventNotification-Ignore"] = True

        c = BeanstalkdConnection("localhost", 11300)
        c.put("{'test': 1}")

        try:
            version, account, container, object = split_path(req.environ['PATH_INFO'], 1, 4, rest_with_last=True)
            curr_level = self.get_current_level(account, container, object)
            upper_level = self.get_upper_level(account, container, object)
            event_configation_changed = False
            if req.method == "POST" and req.query_string == "notification":
                if not curr_level in ["account", "container"]:
                    # cant configure notifications on object level
                    return Response(request=req, status=400, body=b"Invalid configuration", content_type="text/plain")

                notification_sysmeta = get_sys_meta_prefix(curr_level) + 'notifications'
                config = req.body_file.read().strip()
                if not config:
                    req.headers[notification_sysmeta] = ""
                else:
                    if self.configuration_validator.validate(self.destination_handlers, self.payload_handlers, config):
                        req.headers[notification_sysmeta] = config
                    else:
                        # todo: send info about which part of configuration is invalid
                        return Response(request=req, status=400, body=b"Invalid configuration", content_type="text/plain")
                event_configation_changed = True
            resp = req.get_response(self.app)
        except Exception as e:
            self.destination_handlers[get_destination_handler_name("beanstalkd")].connection.put("1:" + str(e))

        try:
            if event_configation_changed:
                self.send_test_notification(curr_level, resp)
            if upper_level:
                self.send_notification(upper_level, resp)
            # todo: better way to test query_string
            if req.method == "GET" and req.query_string and req.query_string.startswith("notification") and resp.is_success: #todo ACL
                info_method = get_container_info if curr_level == "container" else get_account_info
                event_notifications_configuration = self.get_notification_configuration(info_method, req.environ)
                resp.body = str.encode(str(json.loads(event_notifications_configuration)) + '\n' \
                    if event_notifications_configuration else "")

        except Exception as e:
            self.destination_handlers[get_destination_handler_name("beanstalkd")].connection.put("2:" + str(e))

        return resp


def enoss_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    def event_notifications_filter(app):
        return ENOSSMiddleware(app, conf)
    return event_notifications_filter
