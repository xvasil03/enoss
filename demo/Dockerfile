FROM dockerswiftaio/docker-swift:latest

COPY etc/swift/proxy-server.conf-sample /etc/swift/proxy-server.conf
COPY etc/swift/enoss /etc/swift/enoss
COPY swift/common/middleware/enoss /usr/local/src/swift/swift/common/middleware/enoss
COPY test/functional/test_enoss.py /usr/local/src/swift/test/functional/test_enoss.py
COPY test/unit/common/middleware/test_enoss.py /usr/local/src/swift/test/unit/common/middleware/test_enoss.py
COPY requirements.txt /usr/local/src/swift/requirements.txt

COPY demo /usr/local/src/swift/demo
COPY demo/init.sh /usr/local/bin/init.sh
COPY demo/pystalk_listener.py /usr/local/bin/pystalk_listener.py
COPY demo/start.sh /usr/local/bin/start.sh
COPY demo/run_unittest_enoss.sh /usr/local/src/swift/run_unittest_enoss.sh

RUN ["/bin/bash", "/usr/local/bin/init.sh"]

CMD ["/bin/bash", "/usr/local/bin/start.sh"]
