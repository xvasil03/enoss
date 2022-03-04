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


def get_s3_event_name(account, container, object, method):
    res = "s3"
    if object:
        res += ":Object"
    elif container:
        res += ":Bucket"
    else:
        res += ":Account"

    if method in ["PUT", "POST", "COPY"]:
        res += "Created"
    elif method in ["DELETE"]:
        res += "Deleted"
    else:
        res += "Accessed"

    res += ":" + method.title()

    return res

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
        super(EventNotificationsMiddleware, self).__init__(app)
        with open('/usr/local/src/swift/swift/common/middleware/event_notifications/configuration-schema.json', 'r') as file:
            self.schema = json.load(file)

    def __create_payload(self, req):
        try:
            res = str(create_s3_event(req, self.app))
        except Exception as e:
            res = str(e)
        return res

    def __validate_config(self, req, c):
        result = True
        config = req.body_file.read()
        if config:
            try:
                configJson = json.loads(config)
                jsonschema.validate(instance=configJson, schema=self.schema)

                for _, event_destination_configuration in configJson.items():
                    for event_configuration in event_destination_configuration:
                        for _, filter_item in event_configuration.get("Filter", {}).items():
                            for filter_rule in filter_item["FilterRules"]:
                                getattr(filter_rules_module, filter_rule["Name"].title() + "Rule")
                req.headers[get_sys_meta_prefix('container') + 'notifications'] = config
            except Exception as err:
                c.put(str(err))
                result = False
        return result

    def __should_notify(self, req, event_configurations):
        destinations = []
        version, account, container, object = split_path(req.environ['PATH_INFO'], 1, 4, rest_with_last=True)
        method = req.environ.get('swift.orig_req_method', req.request.method)
        event_type = get_s3_event_name(account, container, object, method)
        for destination_key, event_destination_configuration in event_configurations.items():
            for event_configuration in event_destination_configuration:
                matched_event_type = False
                filter_rule_satisfied = not "Filter" in event_configuration
                for allowed_event_type in event_configuration["Events"]:
                    allowed_event_type = allowed_event_type[:-1] if allowed_event_type.endswith("*") else allowed_event_type
                    if event_type.startswith(allowed_event_type):
                        matched_event_type = True
                        break
                if matched_event_type and not filter_rule_satisfied:
                    for _, filter_item in event_configuration.get("Filter", {}).items():
                        filter_rule_satisfied = True
                        for filter_rule in filter_item["FilterRules"]:
                            filter = getattr(filter_rules_module, filter_rule["Name"].title() + "Rule")()
                            if not filter(self.app, req, filter_rule["Value"]):
                                filter_rule_satisfied = False
                                break
                        if filter_rule_satisfied:
                            break
                if matched_event_type and filter_rule_satisfied:
                    destinations.append(destination_key)
                    break
        return destinations





    @wsgify
    def __call__(self, req):
        c = Connection("localhost", 11300)
        event_configation_changed = False
        if req.method == "POST" and req.query_string == "notification":
            event_configation_changed = self.__validate_config(req, c)
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
                        if self.__should_notify(resp, json.loads(event_notifications_configuration)):
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
