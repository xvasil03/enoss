from .irule import IRule
from swift.proxy.controllers.base import get_container_info, get_account_info, get_object_info
from swift.common.utils import split_path

class SuffixRule(IRule):
    def __call__(self, app, request):
        version, account, container, object = split_path(request.environ['PATH_INFO'], 1, 4, rest_with_last=True)
        if object:
            return object.endswith(self.value)
        elif container:
            return container.endswith(self.value)
        return False
