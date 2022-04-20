apt-get install -y python2.7 python3-dev tox liberasurecode-dev git gcc
cp /usr/local/src/swift/test/sample.conf /etc/swift/test.conf

cd /usr/local/src/swift
tox -e py38 test/unit/common/middleware/test_enoss.py
