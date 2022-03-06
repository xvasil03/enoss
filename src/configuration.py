import json
import jsonschema

from swift.common.utils import split_path

from swift.common.middleware.event_notifications.utils import get_s3_event_name
from swift.common.middleware.event_notifications.constants import supported_s3_events
import swift.common.middleware.event_notifications.filter_rules as filter_rules_module


class S3ConfigurationValidator(object):
    def __init__(self, schema_path):
        with open(schema_path, 'r') as file:
            self.schema = json.load(file)

    def validate_event_type(self, config):
        for _, destinations_configuration in config.items():
            for event_configuration in destinations_configuration:
                if any(event not in supported_s3_events for event in event_configuration["Events"]):
                    raise Exception("Unsupported event type")

    def validate_rules(self, config):
        try:
            for _, destinations_configuration in config.items():
                for event_configuration in destinations_configuration:
                    for _, filter_item in event_configuration.get("Filter", {}).items():
                        for filter_rule in filter_item["FilterRules"]:
                            getattr(filter_rules_module, filter_rules_module.get_rule_class_name(filter_rule["Name"]))
        except:
            raise Exception("Unsupported rule operator")


    def validate(self, config):
        try:
            config_json = json.loads(config)
            jsonschema.validate(instance=config_json, schema=self.schema)
            self.validate_event_type(config_json)
            self.validate_rules(config_json)
        except Exception as e:
            return False
        return True


class S3NotifiationConfiguration(object):

    class DestinationConfiguration(object):

        class FilterConfiguration(object):
            def __init__(self, key, config):
                self.key = key
                self.config = config
                self.rules = []
                for rule in config["FilterRules"]:
                    rule_operator = getattr(filter_rules_module, rule["Name"].title() + "Rule")
                    self.rules.append(rule_operator(rule["Value"]))

            def does_satisfy(self, app, request):
                return all(rule(app, request) for rule in self.rules)

        def __init__(self, config):
            self.config = config
            self.id = config["Id"]
            self.allowed_events = config["Events"]
            self.payload_type = config.get("PayloadStructure", "s3")
            self.filters = [self.FilterConfiguration(filter_key, filter_config) for filter_key, filter_config in config.get("Filter", {}).items()]

        def is_allowed_event(self, request):
            version, account, container, object = split_path(request.environ['PATH_INFO'], 1, 4, rest_with_last=True)
            method = request.environ.get('swift.orig_req_method', request.request.method)
            event = get_s3_event_name(account, container, object, method)
            for allowed_event in self.allowed_events:
                if allowed_event.endswith("*"):
                    if event.startswith(allowed_event[:-1]):
                        return True
                else:
                    if allowed_event == event:
                        return True
            return False

        def is_satisfied_rule(self, app, request):
            return any(filter.does_satisfy(app, request) for filter in self.filters)

        def does_satisfy(self, app, request):
            return self.is_allowed_event(request) and self.is_satisfied_rule(app, request)

    def __init__(self, config):
        self.config = json.loads(config)
        self.destinations_configurations = {}
        for destination_configurations_name, destination_configurations in self.config.items():
            for destination_configuration in destination_configurations:
                # <destination_name>Configrations => <destination_name>
                destination_name = destination_configurations_name.rstrip("Configrations").lower()
                self.destinations_configurations.setdefault(destination_name, []).append(self.DestinationConfiguration(destination_configuration))

    def get_satisfied_destinations(self, app, request):
        result = {}
        for destination_name, destination_configurations in self.destinations_configurations.items():
            for destination_configuration in destination_configurations:
                if destination_configuration.does_satisfy(app, request):
                    result.setdefault(destination_name, []).append(destination_configuration)
        return result
