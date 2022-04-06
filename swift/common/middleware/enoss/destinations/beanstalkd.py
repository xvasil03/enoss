
from .idestination import IDestination
import json
from pystalkd.Beanstalkd import Connection as BeanstalkdConnection

class BeanstalkdDestination(IDestination):
    def __init__(self, conf):
        self.conf = conf["beanstalkd"]
        self.connection = BeanstalkdConnection(self.conf["addr"], self.conf["port"]) #todo tube

    def __del__(self):
        self.connection.close()

    def send_notification(self, notification):
        self.connection.put(json.dumps(notification))
