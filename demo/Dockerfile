FROM dockerswiftaio/docker-swift:latest

COPY etc/swift/proxy-server.conf-sample /etc/swift/proxy-server.conf
COPY swift/common/middleware/enoss /usr/local/src/swift/swift/common/middleware/enoss
COPY test/functional/test_enoss.py /usr/local/src/swift/test/functional/test_enoss.py
COPY test/unit/common/middleware/test_enoss.py /usr/local/src/swift/test/unit/common/middleware/test_enoss.py

COPY demo/init.sh /usr/local/bin/init.sh
COPY demo/pystalk_listener.py /usr/local/bin/pystalk_listener.py
COPY demo/start.sh /usr/local/bin/start.sh

RUN ["/bin/bash", "/usr/local/bin/init.sh"]

CMD ["/bin/bash", "/usr/local/bin/start.sh"]
