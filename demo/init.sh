#!/bin/bash

apt-get update
apt-get install beanstalkd
apt-get install python3-pip

pip3 install pystalk
pip3 install jsonschema

#beanstalkd&
#/usr/local/bin/supervisord -n -c /etc/supervisord.conf

#swift-init proxy-server restart
