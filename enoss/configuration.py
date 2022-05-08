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

import json
import jsonschema

from swift.common.utils import split_path
from enoss.utils import (
    get_s3_event_name, get_rule_handlers, get_rule_handler_name,
    get_destination_handler_name, get_payload_handler_name, json_object_hook)
from enoss.constants import supported_s3_events
import enoss.filter_rules as filter_rules_module

filter_rule_handlers = get_rule_handlers([filter_rules_module])


def _remove_suffix(input, suffix):
    return input[:-len(suffix)]

class ConfigurationInvalid(Exception):
    pass


class S3ConfigurationValidator(object):
    def __init__(self, schema_path):
        with open(schema_path, 'r') as file:
            self.schema = json.load(file, object_hook=json_object_hook)

    def validate_schema(self, config_json):
        try:
            jsonschema.validate(instance=config_json, schema=self.schema)
        except jsonschema.ValidationError:
            raise ConfigurationInvalid("Invalid configuration")
        return config_json

    def validate_event_type(self, config):
        for _, destinations_configuration in config.items():
            for event_configuration in destinations_configuration:
                if any(event not in supported_s3_events
                       for event in event_configuration["Events"]):
                    raise ConfigurationInvalid("Unsupported event type")

    def validate_rules(self, config):
        for _, destinations_configuration in config.items():
            for event_configuration in destinations_configuration:
                filter_conf = event_configuration.get("Filter", {})
                for _, filter_item in filter_conf.items():
                    for filter_rule in filter_item["FilterRules"]:
                        handler_name = get_rule_handler_name(
                            filter_rule["Name"])
                        handler = filter_rule_handlers.get(handler_name)
                        err_msg = None
                        if not handler:
                            err_msg = "Unsupported rule operator"
                        elif not handler.validate(filter_rule["Value"]):
                            err_msg = "Invalid rule value"
                        if err_msg:
                            raise ConfigurationInvalid(err_msg)

    def validate_destinations(self, destination_handlers, config):
        for destination_configs in config:
            destination_name = _remove_suffix(
                destination_configs, "Configrations")
            handler_name = get_destination_handler_name(destination_name)
            if handler_name not in destination_handlers:
                raise ConfigurationInvalid("Unsupported destination")

    def validate_payload_structure(self, payload_handlers, config):
        for _, destinations_configuration in config.items():
            for notification_conf in destinations_configuration:
                payload_name = notification_conf.get("PayloadStructure", "s3")
                handler_name = get_payload_handler_name(payload_name)
                if handler_name not in payload_handlers:
                    raise ConfigurationInvalid("Unsupported payload structure")

    def validate(self, destination_handlers, payload_handlers, config_json):
        self.validate_schema(config_json)
        self.validate_event_type(config_json)
        self.validate_rules(config_json)
        self.validate_destinations(destination_handlers, config_json)
        self.validate_payload_structure(payload_handlers, config_json)


class S3NotifiationConfiguration(object):

    class DestinationConfiguration(object):

        class FilterConfiguration(object):
            def __init__(self, key, config):
                self.key = key
                self.config = config
                self.rules = []
                for rule in config["FilterRules"]:
                    rule_handler_name = get_rule_handler_name(rule["Name"])
                    rule_handler = filter_rule_handlers[rule_handler_name]
                    self.rules.append(rule_handler(rule["Value"]))

            def does_satisfy(self, app, resp):
                return all(rule(app, resp) for rule in self.rules)

        def __init__(self, config):
            self.config = config
            self.id = config["Id"]
            self.allowed_events = config["Events"]
            self.payload_type = config.get("PayloadStructure", "s3")
            self.only_succ_events = config.get("OnlySuccessfulEvents", True)
            filer_configs = config.get("Filter", {})
            self.filters = [self.FilterConfiguration(filter_key, filter_config)
                            for filter_key, filter_config
                            in filer_configs.items()]

        def is_allowed_event(self, resp):
            version, account, container, object = split_path(
                resp.environ['PATH_INFO'], 1, 4, rest_with_last=True)
            method = resp.environ.get('swift.orig_req_method',
                                      resp.request.method)
            event = get_s3_event_name(account, container, object, method)
            for allowed_event in self.allowed_events:
                if allowed_event.endswith("*"):
                    if event.startswith(allowed_event[:-1]):
                        return True
                else:
                    if allowed_event == event:
                        return True
            return False

        def is_satisfied_rule(self, app, resp):
            return not self.filters or any(filter.does_satisfy(app, resp)
                                           for filter in self.filters)

        def does_satisfy(self, app, resp):
            return self.is_allowed_event(resp) \
                and self.is_satisfied_rule(app, resp) \
                and (resp.is_success or not self.only_succ_events)

    def __init__(self, config):
        self.config = config if type(config) == dict \
            else json.loads(config, object_hook=json_object_hook)
        self.destinations_configurations = {}
        for dest_confs_name, dest_confs in self.config.items():
            for dest_conf in dest_confs:
                # <dest_name>Configrations => <dest_name>
                dest_name = _remove_suffix(
                    dest_confs_name, "Configrations").lower()
                new_dest_conf = self.DestinationConfiguration(dest_conf)
                self.destinations_configurations.setdefault(dest_name, [])\
                                                .append(new_dest_conf)

    def get_satisfied_destinations(self, app, resp):
        result = {}
        for dest_name, dest_confs in self.destinations_configurations.items():
            for dest_conf in dest_confs:
                if dest_conf.does_satisfy(app, resp):
                    result.setdefault(dest_name, []).append(dest_conf)
        return result
