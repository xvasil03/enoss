FROM dockerswiftaio/docker-swift:latest

COPY . /enoss
COPY etc/swift/enoss /etc/swift/enoss
COPY etc/swift/enoss/proxy-server.conf-sample /etc/swift/proxy-server.conf
COPY test/functional/test_enoss.py /usr/local/src/swift/test/functional/test_enoss.py
COPY test/unit/common/middleware/test_enoss.py /usr/local/src/swift/test/unit/common/middleware/test_enoss.py

RUN ["/bin/bash", "/enoss/demo/init.sh"]

CMD ["/bin/bash", "/enoss/demo/start.sh"]
