import abc

from swift.proxy.controllers.base import get_container_info, get_account_info, get_object_info
from swift.common.utils import split_path

def create_rule_class_name(rule_name):
    return rule_name.title() + "Rule"

class RuleI(object, metaclass=abc.ABCMeta):
    def __init__(self, value):
        self.value = value

    @abc.abstractmethod
    def __call__(self, app, request, filter_value):
        raise NotImplementedError('__call__ is not implemented')


class PrefixRule(RuleI):
    def __call__(self, app, request):
        version, account, container, object = split_path(request.environ['PATH_INFO'], 1, 4, rest_with_last=True)
        if object:
            object.startswith(self.value)
        elif container:
            return container.startswith(self.value)
        return False

class SufixRule(RuleI):
    def __call__(self, app, request):
        version, account, container, object = split_path(request.environ['PATH_INFO'], 1, 4, rest_with_last=True)
        if object:
            object.endswith(self.value)
        elif container:
            return container.endswith(self.value)
        return False
