cd ..
docker build -f demo_openio/Dockerfile . -t oio-enoss
sudo docker run -e OPENIO_IPADDR=127.0.0.41 -e PYTHONUNBUFFERED=1 oio-enoss
