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

from enoss.filter_rules.irule import IRule
from swift.proxy.controllers.base import get_object_info


class ContenttypeRule(IRule):

    @staticmethod
    def validate(value):
        return type(value) == str

    def __call__(self, app, resp):
        method = resp.environ.get('swift.orig_req_method', resp.request.method)
        content_type = None
        if method == "PUT":
            # read content type from request headers
            content_type = resp.environ.get("CONTENT_TYPE")
        elif method in ["GET", "HEAD"]:
            # read content type from respond headers
            content_type = resp.headers.get("Content-Type")
        else:
            # read content type from object storage
            object_info = get_object_info(resp.environ, app)
            if object_info["status"] == 200:
                # if object exists in storage
                content_type = object_info.get("type")
        return content_type and content_type == self.value
