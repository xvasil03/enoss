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

from elasticsearch import Elasticsearch
import json


class ElasticsearchDestination(IDestination):
    def __init__(self, conf):
        self.conf = conf["elasticsearch"]
        self.target_index = self.conf["index"]
        self.es = Elasticsearch(
            self.conf["hosts"],
            ca_certs=self.conf["ca_certs"],
            basic_auth=(self.conf["auth_user"], self.conf["auth_passwd"])
        )
        assert (self.es.ping()), "Cannot connect to elasticsearch"
        # create index if doesnt exist
        if not self.es.indices.exists(index=self.target_index):
            index_mappings = self._get_mappings(
                self.conf.get("index_mappings_file")
            )
            self.es.indices.create(
                index=self.target_index,
                mappings=index_mappings)

    def _get_mappings(self, file_path):
        mapping = None
        if file_path:
            with open(file_path) as f:
                mapping = json.loads(f.read())
        return mapping

    def send_notification(self, notification):
        self.es.index(
            index=self.target_index,
            body=json.dumps(notification)
        )
