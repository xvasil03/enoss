#!/bin/bash

apt-get update
apt-get install -y beanstalkd
apt-get install -y python3-pip
apt-get install -y curl

pip3 install pystalk
pip3 install jsonschema

pip3 install elasticsearch>=8.1.3
pip3 install eventlet>=0.33.0 --upgrade
