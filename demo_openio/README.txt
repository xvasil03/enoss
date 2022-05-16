OPENIO SDS DEMO WITH ENOSS ENABLED

Command (might need root privileges):

bash run_docker_demo.sh

will create and run docker image having OpenIO SDS storage with ENOSS enabled.

Wait 2 mins to initalize then connect to docker container using bash.

script /enoss/demo_openio/demo.sh will enable notification confguration in OpenIO SDS and will create event that will invoke notificaiton.

Notification will be sent to beanstalkd queue.

Event from beanstalkd queue can be read using

python3 /enoss/demo_openio/pystalk_listener.py

----------------------
Limitations: demo exepct that docker container is run on ip address 127.0.0.41
