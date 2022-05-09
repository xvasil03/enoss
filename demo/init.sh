#!/bin/bash

apt-get update
apt-get install -y beanstalkd
apt-get install -y python3-pip
apt-get install -y curl

cd /enoss
pip3 install -r requirements.txt --upgrade
pip3 install .
