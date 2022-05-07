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

from enoss.destinations.idestination import IDestination

import json
from greenstalk import Client

class BeanstalkdDestination(IDestination):
    def __init__(self, conf):
        self.conf = conf["beanstalkd"]
        self.connection = Client((self.conf["addr"], int(self.conf["port"])))
        self.tube = self.conf.get("tube", "default")
        self.connection.use(self.tube)

    def __del__(self):
        self.connection.close()

    def send_notification(self, notification):
        self.connection.put(json.dumps(notification))
