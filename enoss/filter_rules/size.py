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
from swift.common.utils import split_path
from swift.proxy.controllers.base import get_account_info, get_container_info,\
    get_object_info


def _get_size(resp, app):
    size = None
    version, account, container, object = split_path(
        resp.environ['PATH_INFO'], 1, 4, rest_with_last=True)
    if object:
        size = get_object_info(resp.environ, app).get("length")
    else:
        info_method = get_container_info if container else get_account_info
        size = info_method(resp.environ, app).get("bytes")
    return size


class MaxsizeRule(IRule):

    @staticmethod
    def validate(value):
        return type(value) == int

    def __call__(self, app, resp):
        size = _get_size(resp, app)
        return size is not None and self.value >= size


class MinsizeRule(IRule):

    @staticmethod
    def validate(value):
        return type(value) == int

    def __call__(self, app, resp):
        size = _get_size(resp, app)
        return size is not None and self.value <= size
