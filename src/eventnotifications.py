from swift.common.http import is_success
from swift.common.swob import wsgify
from swift.common.utils import split_path, get_logger
from swift.common.request_helpers import get_sys_meta_prefix
from swift.proxy.controllers.base import get_container_info, get_account_info, get_object_info
from eventlet import Timeout
import six

from pystalkd.Beanstalkd import Connection
import json
import jsonschema
from datetime import datetime
from swift.common.wsgi import WSGIContext
from swift.common.swob import Request
import time
from email.utils import parsedate

import swift.common.middleware.event_notifications.filter_rules as filter_rules_module
from swift.common.middleware.event_notifications.utils import get_s3_event_name

from swift.common.middleware.event_notifications.configuration import S3ConfigurationValidator, S3NotifiationConfiguration
from swift.common.middleware.event_notifications.payload import S3NotificationPayload


class EventNotificationsMiddleware(WSGIContext):
    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.logger = get_logger(conf, log_route='eventnotifications')
        self.configuration_validator = S3ConfigurationValidator('/usr/local/src/swift/swift/common/middleware/event_notifications/configuration-schema.json')
        super(EventNotificationsMiddleware, self).__init__(app)

    def __create_payload(self, req):
        try:
            res = str(create_s3_event(req, self.app))
        except Exception as e:
            res = str(e)
        return res

    @wsgify
    def __call__(self, req):
        c = Connection("localhost", 11300)
        event_configation_changed = False
        if req.method == "POST" and req.query_string == "notification":
            config = req.body_file.read()
            if self.configuration_validator.validate(config):
                req.headers[get_sys_meta_prefix('container') + 'notifications'] = config
                event_configation_changed = True
        # swift can call it self recursively => we want only one notification per user request
        req.headers["X-Backend-EventNotification-Ignore"] = True
        resp = req.get_response(self.app)

        if not resp.headers.get("X-Backend-EventNotification-Ignore"):
            if event_configation_changed:
                s3_payload = S3NotificationPayload(self.conf)
                c.put(json.dumps(s3_payload.create_test_payload(self.app, resp)))
            else:
                container = get_container_info(resp.environ, self.app)
                event_notifications_configuration = container.get("sysmeta", {}).get("notifications")
                if event_notifications_configuration:
                    try:
                        s3_configuration = S3NotifiationConfiguration(event_notifications_configuration)
                        if s3_configuration.get_satisfied_destinations(self.app, resp):
                            s3_payload = S3NotificationPayload(self.conf)
                            c.put(json.dumps(s3_payload.create_payload(self.app, resp)))
                    except Exception as e:
                        c.put(str(e))



        return resp


def event_notifications_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    def event_notifications_filter(app):
        return EventNotificationsMiddleware(app, conf)
    return event_notifications_filter
