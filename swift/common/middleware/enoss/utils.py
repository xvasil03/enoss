import sys
import inspect

def get_s3_event_name(account, container, object, method):
    res = "s3"
    if object:
        res += ":Object"
    elif container:
        res += ":Bucket"
    else:
        res += ":Account"

    if method in ["PUT", "POST", "COPY"]:
        res += "Created"
    elif method in ["DELETE"]:
        res += "Deleted"
    else:
        res += "Accessed"

    res += ":" + method.title()

    return res

def __get_handler_class_name(handler_name, handler_suffix):
    return handler_name.title() + handler_suffix.title()

def get_destination_handler_name(destination_name):
    return __get_handler_class_name(destination_name, "Destination")

def get_rule_handler_name(rule_name):
    return __get_handler_class_name(rule_name, "Rule")

def get_payload_handler_name(payload_name):
    return __get_handler_class_name(payload_name, "Payload")

def __get_handlers(handler_modules, handler_suffix):
    handlers = {}
    interface_class_name = "I" + handler_suffix.title()
    for handler_module in handler_modules:
        for (handler_name, handler_class) in inspect.getmembers(sys.modules[handler_module.__name__], inspect.isclass):
            if handler_name.endswith(handler_suffix) and handler_name != interface_class_name:
                handlers[handler_name] = handler_class
    return handlers

def get_payload_handlers(payload_modules):
    return __get_handlers(payload_modules, "Payload")

def get_destination_handlers(destination_modules):
    return __get_handlers(destination_modules, "Destination")

def get_rule_handlers(rule_modules):
    return __get_handlers(rule_modules, "Rule")
