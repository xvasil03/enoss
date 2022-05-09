cd ..
docker build -f demo/Dockerfile . -t swift-enoss
sudo docker run -e RUN_UNIT_TEST_ENOSS='yes' -e RUN_FUNC_TEST_ENOSS='yes' -e PYTHONUNBUFFERED=1 swift-enoss
