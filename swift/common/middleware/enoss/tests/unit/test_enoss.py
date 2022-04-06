import os
import shutil
import tempfile
import unittest

import json

from swift.common.swob import Request, Response

from swift.common.middleware.event_notifications.eventnotifications import EventNotificationsMiddleware
from swift.common.middleware.event_notifications.destination import DestinationI
from swift.common.middleware.event_notifications.payload import PayloadI
from swift.common.middleware.event_notifications.filter_rules import RuleI
from swift.common.middleware.event_notifications.configuration import filter_rule_handlers

#todo fix imports
from helpers import FakeSwift
#from test.debug_logger import debug_logger
from debug_logger import debug_logger

#todo ORDER
class TestEventNotifications(unittest.TestCase):

    def setUp(self):
        self.fake_swift = FakeSwift()
        self.logger = debug_logger('test-event_notifications')

    def tearDown(self):
        pass

    def _steps(self):
        for name in dir(self):
            if name.startswith("step"):
                yield name, getattr(self, name)

    def test_steps(self):
        for name, step in self._steps():
            try:
                step()
            except Exception as e:
                self.fail("{} failed ({}: {})".format(step, type(e), e))

    def step1_init(self):
        app_conf = {
            'destinations': '{"beanstalkd": {"addr": "localhost", "port": 11300, "tube": "default", "handler": "beanstalkd"}}',
            's3_schema': '/usr/local/src/swift/swift/common/middleware/event_notifications/configuration-schema.json'
        }
        # event notification middleware initialize all payload/destination/filter handlers
        self.app = EventNotificationsMiddleware(self.fake_swift, app_conf, logger=self.logger)

    def step2_handlers(self):
        for _, handler in self.app.destination_handlers.items():
            self.assertIsInstance(handler, DestinationI)
        for _, handler in self.app.payload_handlers.items():
            self.assertIsInstance(handler, PayloadI)
        for _, handler in filter_rule_handlers.items():
            self.assertTrue(issubclass(handler, RuleI))

    def step3_configuration(self):
        def validate_config(testing_conf):
            return self.app.configuration_validator.validate(self.app.destination_handlers, self.app.payload_handlers, testing_conf)

        s3_notification_configuration = {
            "BeanstalkdConfigrations": [
              {
                "Id": "test",
                "Events": ["*"],
                "PayloadStructure": "s3",
                "Filter": {
                  "Key": {
                    "FilterRules": [
                      {
                        "Name": "prefix",
                        "Value": ""
                      }
                    ]
                  }
                }
              }
            ]
        }
        self.assertTrue(validate_config(json.dumps(s3_notification_configuration)))

        # unsupported configuration name
        s3_notification_configuration["InvalidNameConfiguration"] = s3_notification_configuration["BeanstalkdConfigrations"]
        self.assertFalse(validate_config(json.dumps(s3_notification_configuration)))
        del s3_notification_configuration["InvalidNameConfiguration"]

        # unsupported event type
        s3_notification_configuration["BeanstalkdConfigrations"][0]["Events"].append("BadEventType")
        self.assertFalse(validate_config(json.dumps(s3_notification_configuration)))
        del s3_notification_configuration["BeanstalkdConfigrations"][0]["Events"][-1]

        # missing value for filter operator
        s3_notification_configuration["BeanstalkdConfigrations"][0]["Filter"]["Key"]["FilterRules"].append({"Name": "suffix"})
        self.assertFalse(validate_config(json.dumps(s3_notification_configuration)))

        # valid filter operator with value
        s3_notification_configuration["BeanstalkdConfigrations"][0]["Filter"]["Key"]["FilterRules"][-1]= {"Name": "suffix", "Value": "a"}
        self.assertTrue(validate_config(json.dumps(s3_notification_configuration)))

        # non existing filter operator
        s3_notification_configuration["BeanstalkdConfigrations"][0]["Filter"]["Key"]["FilterRules"][-1]= {"Name": "non_existing", "Value": "1"}
        self.assertFalse(validate_config(json.dumps(s3_notification_configuration)))
        del s3_notification_configuration["BeanstalkdConfigrations"][0]["Filter"]["Key"]["FilterRules"][-1]

        # not supported payload structure
        s3_notification_configuration["BeanstalkdConfigrations"][0]["PayloadStructure"] = "NotSupportedPayloadStructure"
        self.assertFalse(validate_config(json.dumps(s3_notification_configuration)))

        # default payload structure is s3 which is supported
        del s3_notification_configuration["BeanstalkdConfigrations"][0]["PayloadStructure"]
        self.assertTrue(validate_config(json.dumps(s3_notification_configuration)))

        # one destination can have multiple configurations
        s3_notification_configuration["BeanstalkdConfigrations"].append(s3_notification_configuration["BeanstalkdConfigrations"][0])
        self.assertTrue(validate_config(json.dumps(s3_notification_configuration)))

    def step4_notifications(self):
        pass

if __name__ == '__main__':
    unittest.main()
