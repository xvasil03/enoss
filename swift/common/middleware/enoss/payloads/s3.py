from datetime import datetime
import time
from email.utils import parsedate

from .ipayload import IPayload
from swift.common.utils import split_path
from swift.common.middleware.enoss.utils import get_s3_event_name

class S3Payload(IPayload):

    def create_test_payload(self, app, request, invoking_configuration):
        version, account, container, object = split_path(request.environ['PATH_INFO'], 1, 4, rest_with_last=True)
        event = {
            "Service": "Amazon S3",
            "Event": "s3:TestEvent",
            "Time": datetime.now().isoformat(),
            "Bucket": container,
            "RequestId": request.environ.get("swift.trans_id"),
            "HostId":"TODO"
        }
        return event

    def create_payload(self, app, request, invoking_configuration):
        version, account, container, object = split_path(request.environ['PATH_INFO'], 1, 4, rest_with_last=True)
        method = request.environ.get('swift.orig_req_method', request.request.method)
        object_vesion_id = request.headers.get("X-Object-Version-Id", '')
        sequencer = ""
        if method in ["PUT", "DELETE"]:
            if object_vesion_id:
                # version_id has more accurate timestamp
                sequencer = object_vesion_id
            elif 'Last-Modified' in request.headers:
                sequencer = time.mktime(parsedate(request.headers['Last-Modified']))
        notification_payload = {
            "Records": {
                "eventVersion": "2.2",
                "eventSource": "aws:s3",
                "eventTime": datetime.now().isoformat(), # todo: check if req has timestamp
                "eventName": get_s3_event_name(account, container, object, method),
                "userIdentity":{
                    "principalId": request.environ.get("REMOTE_USER")
                },
                "requestParameters":{
                    "sourceIPAddress": request.environ.get("REMOTE_ADDR")
                },
                "responseElements":{
                    "x-amz-request-id": request.environ.get("swift.trans_id")
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
                        "size": request.headers.get('content-length', 0),
                        "eTag": request.headers.get("etag", ''),
                        "versionId": object_vesion_id,
                        "sequencer": sequencer
                    }
                }
            }
        }
        return notification_payload
