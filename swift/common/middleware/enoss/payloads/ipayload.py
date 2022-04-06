import abc

class IPayload(object, metaclass=abc.ABCMeta):
    def __init__(self, conf):
        self.conf = conf

    @abc.abstractmethod
    def create_test_payload(self, app, request, invoking_configuration):
        raise NotImplementedError('create_test_payload is not implemented')

    @abc.abstractmethod
    def create_payload(self, app, request, invoking_configuration):
        raise NotImplementedError('create_payload is not implemented')
