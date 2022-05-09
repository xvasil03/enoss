#!/usr/bin/python

# Copyright (c) 2022 Nemanja Vasiljevic <xvasil03@gmail.com>
# Copyright (c) 2010-2012 OpenStack Foundation
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
#
# Inspired/Retrived from test_container.py

import json
import unittest
from uuid import uuid4

from test.functional import check_response, retry, load_constraint, SkipTest, \
    requires_acls
import test.functional as tf

import six
from copy import deepcopy


def setUpModule():
    tf.setup_package()


def tearDownModule():
    tf.teardown_package()


class TestENOSS(unittest.TestCase):

    def setUp(self):
        if tf.skip:
            raise SkipTest
        self.name = uuid4().hex
        # this container isn't created by default, but will be cleaned up
        self.container = uuid4().hex

        def put(url, token, parsed, conn):
            conn.request('PUT', parsed.path + '/' + self.name, '',
                         {'X-Auth-Token': token})
            return check_response(conn)

        resp = retry(put)
        resp.read()
        # If the request was received and processed but the container-server
        # timed out getting the response back to the proxy, or the proxy timed
        # out getting the response back to the client, the next retry will 202
        self.assertIn(resp.status, (201, 202))

        self.max_meta_count = load_constraint('max_meta_count')
        self.max_meta_name_length = load_constraint('max_meta_name_length')
        self.max_meta_overall_size = load_constraint('max_meta_overall_size')
        self.max_meta_value_length = load_constraint('max_meta_value_length')

        self.s3_conf_good = {
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
        if tf.skip:
            raise SkipTest

        def get(url, token, parsed, conn, container):
            conn.request(
                'GET', parsed.path + '/' + container + '?format=json', '',
                {'X-Auth-Token': token})
            return check_response(conn)

        def delete(url, token, parsed, conn, container, obj):
            if six.PY2:
                obj_name = obj['name'].encode('utf8')
            else:
                obj_name = obj['name']
            path = '/'.join([parsed.path, container, obj_name])
            conn.request('DELETE', path, '', {'X-Auth-Token': token})
            return check_response(conn)

        for container in (self.name, self.container):
            while True:
                resp = retry(get, container)
                body = resp.read()
                if resp.status == 404:
                    break
                self.assertEqual(resp.status // 100, 2, resp.status)
                objs = json.loads(body)
                if not objs:
                    break
                for obj in objs:
                    resp = retry(delete, container, obj)
                    resp.read()
                    # Under load, container listing may not upate immediately,
                    # so we may attempt to delete the same object multiple
                    # times. Tolerate the object having already been deleted.
                    self.assertIn(resp.status, (204, 404))

        def delete(url, token, parsed, conn, container):
            conn.request('DELETE', parsed.path + '/' + container, '',
                         {'X-Auth-Token': token})
            return check_response(conn)

        for container in (self.name, self.container):
            resp = retry(delete, container)
            resp.read()
            # self.container may not have been created at all, but even if it
            # has, for either container there may be a failure that trips the
            # retry despite the request having been successfully processed.
            self.assertIn(resp.status, (204, 404))

    def post_account(self, url, token, parsed, conn, headers):
        new_headers = dict({'X-Auth-Token': token}, **headers)
        conn.request('POST', parsed.path, '', new_headers)
        return check_response(conn)

    def post_notification(self, url, token, parsed, conn, body=''):
        path = parsed.path + '/' + self.name + "?notification"
        headers = {'X-Auth-Token': token,
                   'Content-Type': 'application/json'}
        body = json.dumps(body) if body and isinstance(body, dict) else body
        conn.request('POST', path, body, headers)
        return check_response(conn)

    def get_notification(self, url, token, parsed, conn):
        path = parsed.path + '/' + self.name + "?notification"
        headers = {'X-Auth-Token': token}
        conn.request('GET', path, '', headers)
        return check_response(conn)

    def initial_state(self):
        resp = retry(self.post_notification)
        self.assertIn(resp.status, (200, 204))
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertFalse(resp.text)

    def test_POST_GET_GOOD_config(self):
        if tf.skip:
            raise SkipTest
        pass

        # store notification config
        resp = retry(self.post_notification, self.s3_conf_good)
        self.assertIn(resp.status, (200, 204))
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertTrue(self.s3_conf_good.items() <= resp.json().items())

        # delete notification config
        resp = retry(self.post_notification)
        self.assertIn(resp.status, (200, 204))
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertFalse(resp.text)

    def test_POST_GET_BAD_GOD_config(self):
        if tf.skip:
            raise SkipTest

        # missing mandatory information
        s3_conf_bad = deepcopy(self.s3_conf_good)
        del s3_conf_bad["BeanstalkdConfigrations"][0]["Events"]
        resp = retry(self.post_notification, s3_conf_bad)
        self.assertEqual(resp.status, 400)
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertFalse(resp.text)

        # invalid/unsupported event type
        s3_conf_bad["BeanstalkdConfigrations"][0]["Events"] = ["InvalidType"]
        resp = retry(self.post_notification, s3_conf_bad)
        self.assertEqual(resp.status, 400)
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertFalse(resp.text)

        # invalid json config
        invalid_json_str = "{test: 1}"
        resp = retry(self.post_notification, invalid_json_str)
        self.assertEqual(resp.status, 400)
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertFalse(resp.text)

        # if config is invalid it should not update stored config in swift
        resp = retry(self.post_notification, self.s3_conf_good)
        self.assertIn(resp.status, (200, 204))
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertTrue(self.s3_conf_good.items() <= resp.json().items())
        stored_config = resp.json()
        resp = retry(self.post_notification, s3_conf_bad)
        self.assertEqual(resp.status, 400)
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertEqual(stored_config, resp.json())

        # return to initial state
        self.initial_state()

    @requires_acls
    def test_acl_get_config(self):
        # store notification config
        resp = retry(self.post_notification, self.s3_conf_good)
        self.assertIn(resp.status, (200, 204))
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertTrue(self.s3_conf_good.items() <= resp.json().items())

        # cannot read config
        resp = retry(self.get_notification, use_account=3)
        resp.read()
        self.assertEqual(resp.status, 403)

        # set read acl
        acl_user = tf.swift_test_user[2]
        acl = {'read-only': [acl_user]}
        headers = {'x-account-access-control': json.dumps(acl)}
        resp = retry(self.post_account, headers=headers, use_account=1)
        resp.read()
        self.assertEqual(resp.status, 204)

        # can read config with read-only acl
        resp = retry(self.get_notification, use_account=3)
        self.assertIn(resp.status, (200, 204))
        self.assertTrue(self.s3_conf_good.items() <= resp.json().items())

        # set read-write acl
        acl_user = tf.swift_test_user[2]
        acl = {'read-write': [acl_user]}
        headers = {'x-account-access-control': json.dumps(acl)}
        resp = retry(self.post_account, headers=headers, use_account=1)
        resp.read()
        self.assertEqual(resp.status, 204)

        # can read config with read-write acl
        resp = retry(self.get_notification, use_account=3)
        self.assertIn(resp.status, (200, 204))
        self.assertTrue(self.s3_conf_good.items() <= resp.json().items())

        # delete notification config
        resp = retry(self.post_notification, use_account=3)
        resp.read()
        self.assertIn(resp.status, (200, 204))
        resp = retry(self.get_notification, use_account=3)
        self.assertIn(resp.status, (200, 204))
        self.assertFalse(resp.text)

        # return to initial state
        self.initial_state()

    @requires_acls
    def test_acl_post_config(self):

        # no acl at all
        resp = retry(self.post_notification, self.s3_conf_good, use_account=3)
        resp.read()
        self.assertEqual(resp.status, 403)
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertFalse(resp.text)

        # set read acl
        acl_user = tf.swift_test_user[2]
        acl = {'read-only': [acl_user]}
        headers = {'x-account-access-control': json.dumps(acl)}
        resp = retry(self.post_account, headers=headers, use_account=1)
        resp.read()
        self.assertEqual(resp.status, 204)

        # read acl still cannot post notification config
        resp = retry(self.post_notification, self.s3_conf_good, use_account=3)
        resp.read()
        self.assertEqual(resp.status, 403)
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertFalse(resp.text)

        # set read-write acl
        acl_user = tf.swift_test_user[2]
        acl = {'read-write': [acl_user]}
        headers = {'x-account-access-control': json.dumps(acl)}
        resp = retry(self.post_account, headers=headers, use_account=1)
        resp.read()
        self.assertEqual(resp.status, 204)

        # read-write can post notification config
        resp = retry(self.post_notification, self.s3_conf_good, use_account=3)
        resp.read()
        self.assertIn(resp.status, (200, 204))
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertTrue(self.s3_conf_good.items() <= resp.json().items())

        # delete notification config
        resp = retry(self.post_notification, use_account=3)
        resp.read()
        self.assertIn(resp.status, (200, 204))
        resp = retry(self.get_notification, use_account=3)
        self.assertIn(resp.status, (200, 204))
        self.assertFalse(resp.text)

        # remove all acl
        headers = {'x-account-access-control': json.dumps({})}
        resp = retry(self.post_account, headers=headers, use_account=1)
        resp.read()
        self.assertEqual(resp.status, 204)

        # no acl => no store
        resp = retry(self.post_notification, self.s3_conf_good, use_account=3)
        resp.read()
        self.assertEqual(resp.status, 403)
        resp = retry(self.get_notification)
        self.assertIn(resp.status, (200, 204))
        self.assertFalse(resp.text)

        # return to initial state
        self.initial_state()


if __name__ == '__main__':
    unittest.main()
