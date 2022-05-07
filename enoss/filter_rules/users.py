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


class UsersinRule(IRule):

    @staticmethod
    def validate(values):
        # list of strings
        return type(values) == list and all(type(x) == str for x in values)

    def __call__(self, app, resp):
        user = resp.environ.get("REMOTE_USER")
        return user in self.values


class UsersoutRule(IRule):

    @staticmethod
    def validate(values):
        # list of strings
        return type(values) == list and all(type(x) == str for x in values)

    def __call__(self, app, resp):
        user = resp.environ.get("REMOTE_USER")
        return user not in self.values
