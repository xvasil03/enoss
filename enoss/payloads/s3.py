# Copyright (c) 2022 Nemanja Vasiljevic <xvasil03@gmail.com>.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
from email.utils import parsedate
import time

from enoss.payloads.ipayload import IPayload
from enoss.utils import get_s3_event_name
from swift.common.utils import split_path
from swift.proxy.controllers.base import get_object_info


class S3Payload(IPayload):

    def create_test_payload(self, app, request, invoking_configuration):
        version, account, container, object = split_path(
            request.environ['PATH_INFO'], 1, 4, rest_with_last=True)
        container = container if isinstance(container, str) else ''
        account = account if isinstance(account, str) else ''

        event = {
            "Service": "Amazon S3",
            "Event": "s3:TestEvent",
            "Time": datetime.now().isoformat(),
            "Bucket": container,
            "RequestId": request.environ.get("swift.trans_id"),
            "HostId": "TODO"
        }
        if container:
            event["Bucket"] = container
        else:
            event["Account"] = account
        return event

    def create_payload(self, app, request, invoking_configuration):
        version, account, container, object = split_path(
            request.environ['PATH_INFO'], 1, 4, rest_with_last=True)
        object = object if isinstance(object, str) else ''
        container = container if isinstance(container, str) else ''
        account = account if isinstance(account, str) else ''

        obj_info = get_object_info(request.environ, app) if object else {}

        method = request.environ.get(
            'swift.orig_req_method', request.request.method)
        event_name = get_s3_event_name(account, container, object, method)
        object_vesion_id = request.headers.get("X-Object-Version-Id", '')
        sequencer = ""
        if method in ["PUT", "DELETE"]:
            if object_vesion_id:
                # version_id has more accurate timestamp
                sequencer = object_vesion_id
            elif 'Last-Modified' in request.headers:
                sequencer = time.mktime(
                    parsedate(request.headers['Last-Modified']))
        notification_payload = {
            "Records": [{
                "eventVersion": "2.2",
                "eventSource": "swift:s3",
                # todo: check if req has timestamp
                "eventTime": datetime.now().isoformat(),
                "eventName": event_name,
                "userIdentity": {
                    "principalId": request.environ.get("REMOTE_USER")
                },
                "requestParameters": {
                    "sourceIPAddress": request.environ.get("REMOTE_ADDR")
                },
                "responseElements": {
                    "x-amz-request-id": request.environ.get("swift.trans_id")
                    # todo: x-amz-host-id
                },
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "todo",
                    "bucket": {
                        "name": container,
                        "ownerIdentity": {
                            "principalId": account
                        },
                        "arn": "arn:aws:s3:::" + container,
                    },
                    "object": {
                        "key": object,
                        "size": obj_info.get("length") if obj_info else 0,
                        "eTag": obj_info.get("eTag") if obj_info else 0,
                        "versionId": object_vesion_id if object else '',
                        "sequencer": sequencer
                    }
                }
            }]
        }
        return notification_payload
