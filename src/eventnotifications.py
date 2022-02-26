from swift.common.http import is_success
from swift.common.swob import wsgify
from swift.common.utils import split_path, get_logger
from swift.common.request_helpers import get_sys_meta_prefix
from swift.proxy.controllers.base import get_container_info, get_account_info, get_object_info
from eventlet import Timeout
import six
if six.PY3:
    from eventlet.green.urllib import request as urllib2
else:
    from eventlet.green import urllib2

from pystalkd.Beanstalkd import Connection
import json
from datetime import datetime
from swift.common.wsgi import WSGIContext
from swift.common.swob import Request
import time
from email.utils import parsedate


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
            "eventTime": datetime.now().isoformat(),
            "eventName": get_s3_event_name(account, container, object, method),
            "userIdentity":{
                "principalId": req.environ.get("REMOTE_USER")
            },
            "requestParameters":{
                "sourceIPAddress": req.environ.get("REMOTE_ADDR")
            },
            "responseElements":{
                "x-amz-request-id": req.environ.get("swift.trans_id")
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

class EventNotificationsMiddleware(WSGIContext):
    def __init__(self, app, conf):
        self.app = app
        self.logger = get_logger(conf, log_route='eventnotifications')
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
        # swift can call it self recursively => we want only one notification per user request
        req.headers["X-Backend-EventNotification-Ignore"] = True
        resp = req.get_response(self.app)
        try:
            if not resp.headers.get("X-Backend-EventNotification-Ignore"):
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
