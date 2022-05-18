#!/bin/bash

nohup /bin/bash /swift/bin/launch.sh &

if [[ ! -z "${RUN_UNIT_TEST_ENOSS}" ]]; then
    echo "Running ENOSS unit test"
    /bin/bash /enoss/demo/run_unittest_enoss.sh
    echo "ENOSS unit test finished"
fi

if [[ ! -z "${RUN_FUNC_TEST_ENOSS}" ]]; then
    echo "Running ENOSS functional test"
    /bin/bash /enoss/demo/run_functest_enoss.sh
    echo "ENOSS functional test finished"
fi

tail -f /dev/null
tail -f /var/log/swift/hourly
ls /var/log/swift
tail -f /var/log/swift/proxy.log
