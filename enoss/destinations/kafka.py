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
from kafka import KafkaProducer


class KafkaDestination(IDestination):
    def __init__(self, conf):
        self.conf = conf["kafka"]
        conn_conf = self._get_conn_conf()
        self.conn = KafkaProducer(**conn_conf)
        self.topic = self.conf["topic"]

    def _get_conn_conf(self):
        conn_prefix = "conn_"
        conn_conf = {key[len(conn_prefix):]:value \
            for key, value in self.conf.items() \
            if key.startswith(conn_prefix)}
        return conn_conf

    def __del__(self):
        self.conn.flush()
        self.conn.close()

    def send_notification(self, notification):
        self.conn.send(self.topic, json.dumps(notification).encode())
