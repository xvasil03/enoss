import abc

class IRule(object, metaclass=abc.ABCMeta):
    def __init__(self, value):
        self.value = value

    @abc.abstractmethod
    def __call__(self, app, request):
        raise NotImplementedError('__call__ is not implemented')
