#!/bin/bash

nohup beanstalkd &
nohup /bin/bash /swift/bin/launch.sh &
python3 /usr/local/bin/pystalk_listener.py
