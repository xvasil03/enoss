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

def create_s3_event(req, app):
    version, account, container, object = split_path(req.environ['PATH_INFO'], 1, 4, rest_with_last=True)
    method = req.environ.get('swift.orig_req_method', req.request.method)
    object_vesion_id = req.headers.get("X-Object-Version-Id", '')
    sequencer = ""
    if method in ["PUT", "DELETE"]:
        if object_vesion_id:
            # version_id has more accurate timestamp
            sequencer = object_vesion_id
        elif 'Last-Modified' in req.headers:
            sequencer = time.mktime(parsedate(req.headers['Last-Modified']))
    event = {
        "Records": {
            "eventVersion": "2.2",
            "eventSource": "aws:s3",
            "eventTime": datetime.now().isoformat(), # todo: check if req has timestamp
            "eventName": get_s3_event_name(account, container, object, method),
            "userIdentity":{
                "principalId": req.environ.get("REMOTE_USER")
            },
            "requestParameters":{
                "sourceIPAddress": req.environ.get("REMOTE_ADDR")
            },
            "responseElements":{
                "x-amz-request-id": req.environ.get("swift.trans_id")
                # todo: x-amz-host-id
            },
            "s3":{
                "s3SchemaVersion": "1.0",
                "configurationId": "todo",
                "bucket":{
                    "name": container,
                    "ownerIdentity":{
                        "principalId": account
                    },
                "arn": "arn:aws:s3:::" + container,
                },
                "object":{
                    "key": object,
                    "size": req.headers.get('content-length', 0),
                    "eTag": req.headers.get("etag", ''),
                    "versionId": object_vesion_id,
                    "sequencer": sequencer
                }
            }
        }
    }
    return event

def create_s3_test_event(req):
    version, account, container, object = split_path(req.environ['PATH_INFO'], 1, 4, rest_with_last=True)
    event = {
        "Service": "Amazon S3",
        "Event": "s3:TestEvent",
        "Time": datetime.now().isoformat(),
        "Bucket": container,
        "RequestId": req.environ.get("swift.trans_id"),
        "HostId":"TODO"
    }
    return event

class EventNotificationsMiddleware(WSGIContext):
    def __init__(self, app, conf):
        self.app = app
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
                c.put(str(create_s3_test_event(resp)))
            else:
                container = get_container_info(resp.environ, self.app)
                event_notifications_configuration = container.get("sysmeta", {}).get("notifications")
                if event_notifications_configuration:
                    try:
                        s3_configuration = S3NotifiationConfiguration(event_notifications_configuration)
                        if s3_configuration.get_satisfied_destinations(self.app, resp):
                            c.put(json.dumps(self.__create_payload(resp)))
                    except Exception as e:
                        c.put(str(e))



        return resp


def event_notifications_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    def event_notifications_filter(app):
        return EventNotificationsMiddleware(app, conf)
    return event_notifications_filter
