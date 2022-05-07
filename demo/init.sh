#!/bin/bash

apt-get update
apt-get install -y beanstalkd
apt-get install -y python3-pip
apt-get install -y curl

pip3 install -r /enoss/requirements.txt --upgrade
pip3 install -i https://test.pypi.org/simple/ enoss
pip3 install pystalk # beanstalk listener
