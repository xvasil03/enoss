import abc

class IDestination(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self, conf):
        raise NotImplementedError('__init__ is not implemented')

    @abc.abstractmethod
    def send_notification(self, notification):
        raise NotImplementedError('send_notification is not implemented')
