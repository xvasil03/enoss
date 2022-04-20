#!/bin/bash

nohup beanstalkd &
nohup /bin/bash /swift/bin/launch.sh &

if [[ ! -z "${RUN_UNIT_TEST_ENOSS}" ]]; then
    echo "Running ENOSS unit test"
    /bin/bash /usr/local/src/swift/run_unittest_enoss.sh
    echo "ENOSS unit test finished"
fi

echo "Beanstalk listening:"
python3 /usr/local/bin/pystalk_listener.py
