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

import unittest
from unittest.mock import patch

import json

from swift.common.swob import HTTPOk, Request

from swift.common.request_helpers import get_sys_meta_prefix

from swift.common.middleware.enoss.configuration import filter_rule_handlers
from swift.common.middleware.enoss.destinations import IDestination
from swift.common.middleware.enoss.enoss import ENOSSMiddleware
from swift.common.middleware.enoss.filter_rules.irule import IRule
from swift.common.middleware.enoss.payloads import IPayload

from test.debug_logger import debug_logger
from test.unit.common.middleware.helpers import FakeSwift


class MockBeanstalkdDestination(object):
    def __init__(self, conf):
        self.reset()

    def reset(self):
        self.state = 'notification not sent'

    def send_notification(self, notification):
        self.state = 'notification sent'


class TestENOSS(unittest.TestCase):

    def setUp(self):
        self.fake_swift = FakeSwift()
        self.logger = debug_logger('test-event_notifications')
        self.test_1_init()
        self.s3_notification_conf = {
            "BeanstalkdConfigrations": [
                {
                    "Id": "test",
                    "Events": ["*"],
                    "PayloadStructure": "s3",
                    "Filter": {
                        "Key": {
                            "FilterRules": [{
                                "Name": "suffix",
                                "Value": ".jpg"
                            }]
                        }
                    }
                }
            ]
        }

    def tearDown(self):
        pass

    def test_1_init(self):
        app_conf = {
            'destinations': '''{
                "beanstalkd": {
                    "addr": "localhost", "port": 11300,
                    "tube": "default", "handler": "beanstalkd"
                }
            }''',
            's3_schema': '/usr/local/src/swift/swift/common/middleware/enoss/'
                         'configuration-schema.json'
        }
        # enoss middleware initializes all payload/destination/filter handlers
        self.app = ENOSSMiddleware(self.fake_swift, app_conf,
                                   logger=self.logger)

    def test_2_handlers(self):
        for _, handler in self.app.destination_handlers.items():
            self.assertIsInstance(handler, IDestination)
        for _, handler in self.app.payload_handlers.items():
            self.assertIsInstance(handler, IPayload)
        for _, handler in filter_rule_handlers.items():
            self.assertTrue(issubclass(handler, IRule))

    def test_3_configuration(self):
        def validate_config(testing_conf):
            return self.app.configuration_validator.validate(
                self.app.destination_handlers,
                self.app.payload_handlers,
                testing_conf)

        self.assertTrue(validate_config(json.dumps(self.s3_notification_conf)))

        beanstalkd_conf = self.s3_notification_conf["BeanstalkdConfigrations"]

        # unsupported configuration name
        self.s3_notification_conf["InvalidNameConfiguration"] = beanstalkd_conf
        validation_res = validate_config(json.dumps(self.s3_notification_conf))
        self.assertFalse(validation_res)
        del self.s3_notification_conf["InvalidNameConfiguration"]

        # unsupported event type
        beanstalkd_conf[0]["Events"].append("BadEventType")
        validation_res = validate_config(json.dumps(self.s3_notification_conf))
        self.assertFalse(validation_res)
        del beanstalkd_conf[0]["Events"][-1]

        # missing value for filter operator
        conf_rules = beanstalkd_conf[0]["Filter"]["Key"]["FilterRules"]
        conf_rules.append({"Name": "suffix"})
        validation_res = validate_config(json.dumps(self.s3_notification_conf))
        self.assertFalse(validation_res)

        # valid filter operator with value
        conf_rules[-1] = {"Name": "suffix", "Value": "a"}
        self.assertTrue(validate_config(json.dumps(self.s3_notification_conf)))

        # non existing filter operator
        conf_rules[-1] = {"Name": "non_existing", "Value": "1"}
        validation_res = validate_config(json.dumps(self.s3_notification_conf))
        self.assertFalse(validation_res)
        del conf_rules[-1]

        # not supported payload structure
        beanstalkd_conf[0]["PayloadStructure"] = "NotSupportedPayloadStructure"
        validation_res = validate_config(json.dumps(self.s3_notification_conf))
        self.assertFalse(validation_res)

        # default payload structure is s3 which is supported
        del beanstalkd_conf[0]["PayloadStructure"]
        validation_res = validate_config(json.dumps(self.s3_notification_conf))
        self.assertTrue(validation_res)

        # one destination can have multiple configurations
        beanstalkd_conf.append(beanstalkd_conf[0])
        self.assertTrue(validate_config(json.dumps(self.s3_notification_conf)))

    @patch('swift.common.middleware.enoss.destinations.BeanstalkdDestination',
           new=MockBeanstalkdDestination)
    def test_4_post_configuration_valid(self):
        self.test_1_init()
        self.fake_swift.register('POST', '/v1/a/c1', HTTPOk, {}, 'passed')
        beanstalkd = self.app.destination_handlers["BeanstalkdDestination"]
        beanstalkd.reset()

        infocache = {
            'account/a': {
                'meta': {}
            },
            'container/a/c1': {
                'sysmeta': {
                    'notifications': json.dumps(self.s3_notification_conf)
                }
            }
        }

        req = Request.blank(
            '/v1/a/c1?notification',
            environ={'REQUEST_METHOD': 'POST', 'swift.infocache': infocache},
            body=json.dumps(self.s3_notification_conf)
        )
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        # check if test event is sent
        self.assertEqual(beanstalkd.state, 'notification sent')

        stored_configuration = req.headers.get(get_sys_meta_prefix("container")
                                               + "notifications")
        # check if configuration is stored to sysmetadata
        self.assertIsInstance(stored_configuration, str)
        stored_configuration = json.loads(stored_configuration)
        for key in self.s3_notification_conf:
            self.assertEqual(self.s3_notification_conf[key],
                             stored_configuration[key])

    @patch('swift.common.middleware.enoss.destinations.BeanstalkdDestination',
           new=MockBeanstalkdDestination)
    def test_5_post_configuration_invalid(self):
        self.test_1_init()
        beanstalkd = self.app.destination_handlers["BeanstalkdDestination"]
        beanstalkd.reset()
        self.fake_swift.register('POST', '/v1/a/c1', HTTPOk, {}, 'passed')
        self.fake_swift.register('POST', '/v1/a/c1/o1', HTTPOk, {}, 'passed')

        infocache = {'account/a': {'meta': {}}, 'container/a/c1': {'meta': {}}}

        invalid_notification_configuration = {"invalid": True}
        req = Request.blank(
            '/v1/a/c1?notification',
            environ={'REQUEST_METHOD': 'POST', 'swift.infocache': infocache},
            body=json.dumps(invalid_notification_configuration)
        )
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 400)

        # notification configuration can't be stored in object level
        req = Request.blank(
            '/v1/a/c1/o1?notification',
            environ={'REQUEST_METHOD': 'POST', 'swift.infocache': infocache},
            body=json.dumps(self.s3_notification_conf)
        )
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 403)
        self.assertEqual(beanstalkd.state, 'notification not sent')

    def test_6_read_configuration(self):
        self.fake_swift.register('GET', '/v1/a2', HTTPOk, {}, 'passed')
        self.fake_swift.register('GET', '/v1/a2/c2', HTTPOk, {}, 'passed')

        infocache = {'account/a2': {'sysmeta': {}},
                     'container/a2/c2': {'sysmeta': {}}}
        req = Request.blank(
            '/v1/a2/c2?notification',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache}
        )
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(res.body, b'')

        req = Request.blank(
            '/v1/a2?notification',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache}
        )
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(res.body, b'')

        infocache = {
            'account/a2': {'sysmeta': {}},
            'container/a2/c2': {
                'sysmeta': {
                    'notifications': json.dumps(self.s3_notification_conf)
                }
            }
        }
        req = Request.blank(
            '/v1/a2/c2?notification',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache}
        )
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        body = res.body.decode('utf8').replace("'", '"')
        self.assertEqual(json.loads(body), self.s3_notification_conf)

        infocache = {
            'account/a2': {
                'sysmeta': {
                    'notifications': json.dumps(self.s3_notification_conf)
                }
            },
            'container/a2/c2': {'sysmeta': {}}
        }
        req = Request.blank(
            '/v1/a2?notification',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache}
        )
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        body = res.body.decode('utf8').replace("'", '"')
        self.assertEqual(json.loads(body), self.s3_notification_conf)

    @patch('swift.common.middleware.enoss.destinations.BeanstalkdDestination',
           new=MockBeanstalkdDestination)
    def test_7_send_notification_container_level(self):
        self.test_1_init()
        self.fake_swift.register('GET', '/v1/a3/c3/o3',
                                 HTTPOk, {}, 'passed')
        self.fake_swift.register('GET', '/v1/a3/c3/o3.jpg',
                                 HTTPOk, {}, 'passed')

        beanstalkd = self.app.destination_handlers["BeanstalkdDestination"]
        beanstalkd.reset()

        infocache = {
            'account/a3': {'sysmeta': {}},
            'container/a3/c3': {
                'sysmeta': {
                    'notifications': json.dumps(self.s3_notification_conf)
                }
            }
        }
        req = Request.blank(
            '/v1/a3/c3/o3',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache}
        )
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(beanstalkd.state, 'notification not sent')

        beanstalkd.reset()
        req = Request.blank(
            '/v1/a3/c3/o3.jpg',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache}
        )
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(beanstalkd.state, 'notification sent')

    @patch('swift.common.middleware.enoss.destinations.BeanstalkdDestination',
           new=MockBeanstalkdDestination)
    def test_8_send_notification_account_level(self):
        self.test_1_init()
        self.fake_swift.register('GET', '/v1/a4/c4', HTTPOk, {}, 'passed')
        self.fake_swift.register('GET', '/v1/a4/c4.jpg', HTTPOk, {}, 'passed')

        beanstalkd = self.app.destination_handlers["BeanstalkdDestination"]
        beanstalkd.reset()

        infocache = {
            'account/a4': {
                'sysmeta': {
                    'notifications': json.dumps(self.s3_notification_conf)
                }
            },
            'container/a4/c4': {'sysmeta': {}}
        }
        req = Request.blank(
            '/v1/a4/c4',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache}
        )
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(beanstalkd.state, 'notification not sent')

        beanstalkd.reset()
        req = Request.blank(
            '/v1/a4/c4.jpg',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache}
        )
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(beanstalkd.state, 'notification sent')
        # todo fix ResourceWarning


if __name__ == '__main__':
    unittest.main()
