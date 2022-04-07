import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import json

from swift.common.swob import Request, Response, HTTPOk, HTTPUnauthorized
from swift.common.request_helpers import get_sys_meta_prefix

from swift.common.middleware.enoss.enoss import ENOSSMiddleware, enoss_factory
from swift.common.middleware.enoss.destinations import IDestination
from swift.common.middleware.enoss.payloads import IPayload
from swift.common.middleware.enoss.filter_rules import IRule
from swift.common.middleware.enoss.configuration import filter_rule_handlers

from helpers import FakeSwift
#from test.debug_logger import debug_logger
from debug_logger import debug_logger

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
        self.s3_notification_configuration = {
            "BeanstalkdConfigrations": [
              {
                "Id": "test",
                "Events": ["*"],
                "PayloadStructure": "s3",
                "Filter": {
                  "Key": {
                    "FilterRules": [
                      {
                        "Name": "suffix",
                        "Value": ".jpg"
                      }
                    ]
                  }
                }
              }
            ]
        }

    def tearDown(self):
        pass

    def test_1_init(self):
        app_conf = {
            'destinations': '{"beanstalkd": {"addr": "localhost", "port": 11300, "tube": "default", "handler": "beanstalkd"}}',
            's3_schema': '/usr/local/src/swift/swift/common/middleware/enoss/configuration-schema.json'
        }
        # event notification middleware initialize all payload/destination/filter handlers
        self.app = ENOSSMiddleware(self.fake_swift, app_conf, logger=self.logger)

    def test_2_handlers(self):
        for _, handler in self.app.destination_handlers.items():
            self.assertIsInstance(handler, IDestination)
        for _, handler in self.app.payload_handlers.items():
            self.assertIsInstance(handler, IPayload)
        for _, handler in filter_rule_handlers.items():
            self.assertTrue(issubclass(handler, IRule))

    def test_3_configuration(self):
        def validate_config(testing_conf):
            return self.app.configuration_validator.validate(self.app.destination_handlers, self.app.payload_handlers, testing_conf)

        self.assertTrue(validate_config(json.dumps(self.s3_notification_configuration)))

        # unsupported configuration name
        self.s3_notification_configuration["InvalidNameConfiguration"] = self.s3_notification_configuration["BeanstalkdConfigrations"]
        self.assertFalse(validate_config(json.dumps(self.s3_notification_configuration)))
        del self.s3_notification_configuration["InvalidNameConfiguration"]

        # unsupported event type
        self.s3_notification_configuration["BeanstalkdConfigrations"][0]["Events"].append("BadEventType")
        self.assertFalse(validate_config(json.dumps(self.s3_notification_configuration)))
        del self.s3_notification_configuration["BeanstalkdConfigrations"][0]["Events"][-1]

        # missing value for filter operator
        self.s3_notification_configuration["BeanstalkdConfigrations"][0]["Filter"]["Key"]["FilterRules"].append({"Name": "suffix"})
        self.assertFalse(validate_config(json.dumps(self.s3_notification_configuration)))

        # valid filter operator with value
        self.s3_notification_configuration["BeanstalkdConfigrations"][0]["Filter"]["Key"]["FilterRules"][-1]= {"Name": "suffix", "Value": "a"}
        self.assertTrue(validate_config(json.dumps(self.s3_notification_configuration)))

        # non existing filter operator
        self.s3_notification_configuration["BeanstalkdConfigrations"][0]["Filter"]["Key"]["FilterRules"][-1]= {"Name": "non_existing", "Value": "1"}
        self.assertFalse(validate_config(json.dumps(self.s3_notification_configuration)))
        del self.s3_notification_configuration["BeanstalkdConfigrations"][0]["Filter"]["Key"]["FilterRules"][-1]

        # not supported payload structure
        self.s3_notification_configuration["BeanstalkdConfigrations"][0]["PayloadStructure"] = "NotSupportedPayloadStructure"
        self.assertFalse(validate_config(json.dumps(self.s3_notification_configuration)))

        # default payload structure is s3 which is supported
        del self.s3_notification_configuration["BeanstalkdConfigrations"][0]["PayloadStructure"]
        self.assertTrue(validate_config(json.dumps(self.s3_notification_configuration)))

        # one destination can have multiple configurations
        self.s3_notification_configuration["BeanstalkdConfigrations"].append(self.s3_notification_configuration["BeanstalkdConfigrations"][0])
        self.assertTrue(validate_config(json.dumps(self.s3_notification_configuration)))

    def test_4_post_configuration_valid(self):
        self.fake_swift.register('POST', '/v1/a/c1', HTTPOk, {}, 'passed')

        infocache = {'account/a': {'meta':{}}, 'container/a/c1': {'meta':{}}}

        req = Request.blank('/v1/a/c1?notification',
            environ={'REQUEST_METHOD': 'POST', 'swift.infocache': infocache}, body=json.dumps(self.s3_notification_configuration))

        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)

        stored_configuration = req.headers.get(get_sys_meta_prefix("container") + "notifications")
        # check if configuration is stored to sysmetadata
        self.assertIsInstance(stored_configuration, str)
        stored_configuration = json.loads(stored_configuration)
        for key in self.s3_notification_configuration:
            self.assertEqual(self.s3_notification_configuration[key], stored_configuration[key])

    def test_5_post_configuration_invalid(self):
        self.fake_swift.register('POST', '/v1/a/c1', HTTPOk, {}, 'passed')
        self.fake_swift.register('POST', '/v1/a/c1/o1', HTTPOk, {}, 'passed')

        infocache = {'account/a': {'meta':{}}, 'container/a/c1': {'meta':{}}}

        invalid_notification_configuration = {"invalid": True}
        req = Request.blank('/v1/a/c1?notification',
            environ={'REQUEST_METHOD': 'POST', 'swift.infocache': infocache}, body=json.dumps(invalid_notification_configuration))
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 400)

        # notification configuration can't be stored in object level
        req = Request.blank('/v1/a/c1/o1?notification',
            environ={'REQUEST_METHOD': 'POST', 'swift.infocache': infocache}, body=json.dumps(self.s3_notification_configuration))
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 400)

    def test_6_read_configuration(self):
        self.fake_swift.register('GET', '/v1/a2', HTTPOk, {}, 'passed')
        self.fake_swift.register('GET', '/v1/a2/c2', HTTPOk, {}, 'passed')

        infocache = {'account/a2': {'sysmeta':{}}, 'container/a2/c2': {'sysmeta':{}}}
        req = Request.blank('/v1/a2/c2?notification',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache})
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(res.body, b'')

        req = Request.blank('/v1/a2?notification',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache})
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(res.body, b'')

        infocache = {'account/a2': {'sysmeta':{}},
            'container/a2/c2': {'sysmeta':{'notifications': json.dumps(self.s3_notification_configuration)}}}
        req = Request.blank('/v1/a2/c2?notification',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache})
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        body = res.body.decode('utf8').replace("'", '"')
        self.assertEqual(json.loads(body), self.s3_notification_configuration)

        infocache = {'account/a2': {'sysmeta':{'notifications': json.dumps(self.s3_notification_configuration)}},
            'container/a2/c2':  {'sysmeta': ''}}
        req = Request.blank('/v1/a2?notification',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache})
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        body = res.body.decode('utf8').replace("'", '"')
        self.assertEqual(json.loads(body), self.s3_notification_configuration)

    @patch('swift.common.middleware.enoss.destinations.BeanstalkdDestination', new=MockBeanstalkdDestination)
    def test_7_send_notification_container_level(self):
        self.test_1_init()
        self.fake_swift.register('GET', '/v1/a3/c3/o3', HTTPOk, {}, 'passed')
        self.fake_swift.register('GET', '/v1/a3/c3/o3.jpg', HTTPOk, {}, 'passed')

        beanstalkd_destination = self.app.destination_handlers["BeanstalkdDestination"]
        beanstalkd_destination.reset()

        infocache = {'account/a3': {'sysmeta': ''},
            'container/a3/c3': {'sysmeta':{'notifications': json.dumps(self.s3_notification_configuration)}}}
        req = Request.blank('/v1/a3/c3/o3',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache})
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(beanstalkd_destination.state, 'notification not sent')

        beanstalkd_destination.reset()
        req = Request.blank('/v1/a3/c3/o3.jpg',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache})
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(beanstalkd_destination.state, 'notification sent')

    @patch('swift.common.middleware.enoss.destinations.BeanstalkdDestination', new=MockBeanstalkdDestination)
    def test_8_send_notification_account_level(self):
        self.test_1_init()
        self.fake_swift.register('GET', '/v1/a4/c4', HTTPOk, {}, 'passed')
        self.fake_swift.register('GET', '/v1/a4/c4.jpg', HTTPOk, {}, 'passed')

        beanstalkd_destination = self.app.destination_handlers["BeanstalkdDestination"]
        beanstalkd_destination.reset()

        infocache = {'account/a4': {'sysmeta':{'notifications': json.dumps(self.s3_notification_configuration)}},
            'container/a4/c4': {'sysmeta': ''}}
        req = Request.blank('/v1/a4/c4',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache})
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(beanstalkd_destination.state, 'notification not sent')

        beanstalkd_destination.reset()
        req = Request.blank('/v1/a4/c4.jpg',
            environ={'REQUEST_METHOD': 'GET', 'swift.infocache': infocache})
        res = req.get_response(self.app)
        self.assertEqual(res.status_int, 200)
        self.assertEqual(beanstalkd_destination.state, 'notification sent')
        #todo fix ResourceWarning





if __name__ == '__main__':
    unittest.main()
