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


class HttpcodesRule(IRule):

    @staticmethod
    def validate(values):
        # values must be a list of strings (e.g. ["200", "404", "4xx"])
        allowed_chars = ['x', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        if type(values) != list:
            return False
        for val in values:
            if type(val) != str or any(x not in allowed_chars for x in val):
                return False
        return True

    def _cmp(self, val_1, val_2):
        if len(val_1) != len(val_2):
            return False
        for i in range(len(val_1)):
            if val_1[i] != val_2[i] and val_2[i] != 'x':
                return False
        return True

    def __call__(self, app, resp):
        status = str(resp.status_int)
        return any(self._cmp(status, x) for x in self.value)
