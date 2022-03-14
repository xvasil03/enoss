
import abc
import json

from pystalkd.Beanstalkd import Connection as BeanstalkdConnection

class DestinationI(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self, conf):
        raise NotImplementedError('__init__ is not implemented')

    @abc.abstractmethod
    def send_notification(self, notification):
        raise NotImplementedError('send_notification is not implemented')

class BeanstalkdDestination(DestinationI):
    def __init__(self, conf):
        self.conf = conf["beanstalkd"]
        self.connection = BeanstalkdConnection(self.conf["addr"], self.conf["port"]) #todo tube

    def __del__(self):
        self.connection.close()

    def send_notification(self, notification):
        self.connection.put(json.dumps(notification))
