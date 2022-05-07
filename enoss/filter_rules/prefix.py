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


class PrefixRule(IRule):

    @staticmethod
    def validate(value):
        return type(value) == str

    def __call__(self, app, resp):
        version, account, container, object = split_path(
            resp.environ['PATH_INFO'], 1, 4, rest_with_last=True)
        if object:
            return object.startswith(self.value)
        elif container:
            return container.startswith(self.value)
        return False
