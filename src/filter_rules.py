import abc

from swift.proxy.controllers.base import get_container_info, get_account_info, get_object_info
from swift.common.utils import split_path

class RuleI(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __call__(self, app, request, filter_value):
        raise NotImplementedError('__call__ is not implemented')


class PrefixRule(RuleI):
    def __call__(self, app, request, filter_value):
        version, account, container, object = split_path(request.environ['PATH_INFO'], 1, 4, rest_with_last=True)
        if object:
            object.startswith(filter_value)
        elif container:
            return container.startswith(filter_value)
        return False

class SufixRule(RuleI):
    def __call__(self, app, request, filter_value):
        version, account, container, object = split_path(request.environ['PATH_INFO'], 1, 4, rest_with_last=True)
        if object:
            object.endswith(filter_value)
        elif container:
            return container.endswith(filter_value)
        return False
