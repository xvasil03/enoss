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

import sys

from enoss.destinations.beanstalkd import BeanstalkdDestination
from enoss.destinations.kafka import KafkaDestination

__all__ = [
    'BeanstalkdDestination',
    'KafkaDestination'
]


if sys.version_info[0] >= 3:
    from enoss.destinations.elasticsearch import ElasticsearchDestination
    __all__.append('ElasticsearchDestination')
